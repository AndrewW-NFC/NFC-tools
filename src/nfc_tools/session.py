"""Coordinates a recording session: schedule, recorder, per-segment analysis."""

from __future__ import annotations

import asyncio
import contextlib
import platform
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from . import analyzers, manifest
from .config import Config
from .devices import list_input_devices
from .lock import FileLock, LockTimeout
from .logging_setup import get
from .notifications import notify
from .paths import night_dir
from .recorder import Recorder
from .scheduler import compute_window
from .sounddevice_recorder import SounddeviceRecorder
from .session_logging import append_log_row, read_log_rows
from .weather import append_environment_csv, environmental_snapshot, snapshot

log = get("session")

def _normalize_evening_start(win):
    """Treat morning-looking dusk starts as PM for overnight NFC sessions."""
    if (
        win.starts_at.hour < 12
        and win.ends_at.date() > win.starts_at.date()
        and win.ends_at.hour < 12
    ):
        win.starts_at = win.starts_at + timedelta(hours=12)
    return win


class Session:
    def __init__(self, cfg: Config, on_status: Optional[Callable[[dict], None]] = None):
        self.cfg = cfg
        self.on_status = on_status or (lambda s: None)
        self._recorder: Optional[Recorder] = None
        self._start_task: Optional[asyncio.Task] = None
        self._end_task: Optional[asyncio.Task] = None
        self._pool = ThreadPoolExecutor(max_workers=2)
        self._status: dict = {
            "state": "idle",
            "session_date": None,
            "started_at": None,
            "scheduled_starts_at": None,
            "scheduled_ends_at": None,
            "ends_at": None,
            "recordings": [],
            "level_db": None,
            "weather": None,
            "recorder_diagnostics": None,
            "analysis": {
                "active": False,
                "current_file": None,
                "current_analyzer": None,
                "message": "Analysis will start soon after recording stops.",
                "queue": [],
                "history": [],
            },
            "session_log": [],
        }
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._session_log_rows: list[dict] = []
        self._session_log_path: Optional[Path] = None
        self._recording_log_task: Optional[asyncio.Task] = None
        self._environment_task: Optional[asyncio.Task] = None
        self._logged_environment_hours: set[str] = set()

    @property
    def status(self) -> dict:
        return dict(self._status)

    def _set_status(self, **kw) -> None:
        self._status.update(kw)
        try:
            self.on_status(self.status)
        except Exception:  # noqa: BLE001
            pass


    def _prepare_session_log(self, nd: Path, *, reset_rows: bool = False) -> None:
        """Point this Session at the night's CSV log file."""
        path = nd / "logs" / "session_log.csv"
        if self._session_log_path != path:
            self._session_log_path = path
            self._session_log_rows = read_log_rows(path, limit=1000)
            self._status["session_log"] = list(self._session_log_rows)
        elif reset_rows:
            self._session_log_rows = []
            self._status["session_log"] = []

    def _add_session_log(self, event: str, message: str, **details) -> None:
        """Append one realtime/dashboard log row and write it to CSV."""
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "event": event,
            "message": message,
            "session_date": self._status.get("session_date") or details.pop("session_date", ""),
            "state": self._status.get("state") or details.pop("state", ""),
            "filename": details.pop("filename", ""),
            "analyzer": details.pop("analyzer", ""),
            "level_db": self._status.get("level_db") if self._status.get("level_db") is not None else details.pop("level_db", ""),
            "details": details,
        }

        if self._session_log_path:
            row = append_log_row(self._session_log_path, row)

        self._session_log_rows.append(row)
        self._session_log_rows = self._session_log_rows[-1000:]
        self._status["session_log"] = list(self._session_log_rows)
        try:
            self.on_status(self.status)
        except Exception:  # noqa: BLE001
            pass

    def _write_environment_snapshot(self, nd: Path, when: datetime | None = None) -> None:
        when = when or datetime.now()
        hour_key = when.replace(minute=0, second=0, microsecond=0).isoformat(timespec="minutes")
        if hour_key in self._logged_environment_hours:
            return

        row = environmental_snapshot(
            self.cfg.site.latitude,
            self.cfg.site.longitude,
            self.cfg.site.timezone,
            when,
        )
        append_environment_csv(nd, row)
        self._logged_environment_hours.add(hour_key)

        if row.get("available"):
            msg = f"Environmental conditions logged for {row.get('hour_local')}"
        else:
            msg = f"Environmental conditions unavailable for {row.get('hour_local')}"
        self._add_session_log("environment", msg, environment=row)

    async def _environment_loop(self, nd: Path) -> None:
        try:
            while self._status.get("state") == "recording":
                self._write_environment_snapshot(nd, datetime.now())
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("environment loop stopped: %s", e)
            self._add_session_log("warning", f"Environmental logging stopped: {e}")

    async def _recording_log_loop(self) -> None:
        try:
            while self._status.get("state") == "recording":
                recordings = len(self._status.get("recordings") or [])
                self._add_session_log(
                    "recording_status",
                    "Recording continues.",
                    recordings_completed=recordings,
                    ends_at=self._status.get("ends_at"),
                )
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            log.warning("recording log loop stopped: %s", e)

    def _resolve_device_record(self) -> dict:
        dev_id = self.cfg.recording.device
        for d in list_input_devices():
            if d["id"] == dev_id:
                return d
        raise RuntimeError(
            f"Configured input device '{dev_id}' not found. "
            "Open Settings to choose a different mic."
        )

    def _resolve_device(self) -> list[str]:
        return self._resolve_device_record()["ffmpeg_input"]


    def _select_recording_backend(self) -> str:
        """Return the actual recording backend for this session.

        Auto prefers sounddevice/CoreAudio on macOS because ffmpeg/avfoundation
        produced recurring short spikes in tests while sounddevice was clean.
        Other platforms keep ffmpeg as the default until tested.
        """
        backend = str(getattr(self.cfg.recording, "backend", "auto") or "auto").lower()
        if backend in {"sounddevice", "coreaudio", "sounddevice_coreaudio"}:
            return "sounddevice"
        if backend in {"ffmpeg", "avfoundation", "ffmpeg_avfoundation"}:
            return "ffmpeg"
        if platform.system() == "Darwin":
            return "sounddevice"
        return "ffmpeg"

    def _window_for_start_button(self, now: datetime):
        """Return the relevant scheduled window for the Dashboard start button."""
        win = compute_window(now, self.cfg.schedule.start_time, self.cfg.schedule.end_time)
        win = _normalize_evening_start(win)
        if now >= win.ends_at:
            win = compute_window(
                now + timedelta(hours=12),
                self.cfg.schedule.start_time,
                self.cfg.schedule.end_time,
            )
            win = _normalize_evening_start(win)
        return win

    async def start(self, force: bool = False) -> None:
        if self._status["state"] != "idle":
            raise RuntimeError("Session already running")

        self._loop = asyncio.get_running_loop()
        now = datetime.now()
        win = self._window_for_start_button(now)

        if not force and now < win.starts_at:
            nd = night_dir(win.session_date.isoformat())
            self._prepare_session_log(nd)
            self._set_status(
                state="awaiting_start",
                session_date=win.session_date.isoformat(),
                started_at=None,
                scheduled_starts_at=win.starts_at.isoformat(timespec="seconds"),
                scheduled_ends_at=win.ends_at.isoformat(timespec="seconds"),
                ends_at=win.ends_at.isoformat(timespec="seconds"),
                recordings=[],
                level_db=None,
                weather=None,
            )
            self._add_session_log(
                "session_scheduled",
                "Session scheduled and waiting for start time.",
                scheduled_starts_at=win.starts_at.isoformat(timespec="seconds"),
                scheduled_ends_at=win.ends_at.isoformat(timespec="seconds"),
            )
            self._start_task = asyncio.create_task(self._auto_start_at(win.starts_at, win.ends_at))
            return

        if force:
            session_date = now.date()
            starts_at = now
            ends_at = win.ends_at if win.ends_at > now else now + timedelta(hours=1)
        else:
            session_date = win.session_date
            starts_at = win.starts_at
            ends_at = win.ends_at

        await self._begin_recording(session_date, starts_at, ends_at)

    async def _auto_start_at(self, starts_at: datetime, ends_at: datetime) -> None:
        while True:
            now = datetime.now()
            if now >= starts_at:
                log.info("scheduled start reached; recording")
                await self._begin_recording(starts_at.date(), starts_at, ends_at)
                return
            await asyncio.sleep(min(30.0, max(1.0, (starts_at - now).total_seconds())))

    async def _begin_recording(self, session_date, starts_at: datetime, ends_at: datetime) -> None:
        nd = night_dir(session_date.isoformat())
        self._prepare_session_log(nd)
        self._logged_environment_hours = set()
        device_record = self._resolve_device_record()
        device = device_record["ffmpeg_input"]
        recording_backend = self._select_recording_backend()
        weather = snapshot(self.cfg.site.latitude, self.cfg.site.longitude, self.cfg.site.timezone)

        self._set_status(
            state="recording",
            session_date=session_date.isoformat(),
            started_at=datetime.now().isoformat(timespec="seconds"),
            scheduled_starts_at=starts_at.isoformat(timespec="seconds"),
            scheduled_ends_at=ends_at.isoformat(timespec="seconds"),
            ends_at=ends_at.isoformat(timespec="seconds"),
            recordings=[],
            weather=weather.to_dict(),
        )

        recorder_metadata = {
            "recording_backend": recording_backend,
            "configured_device_id": self.cfg.recording.device,
            "selected_device_id": device_record.get("id", ""),
            "selected_device_name": device_record.get("name", ""),
            "ffmpeg_input": device,
            "sample_rate": self.cfg.recording.sample_rate,
            "channels": self.cfg.recording.channels,
            "bit_depth": self.cfg.recording.bit_depth,
            "segment_seconds": self.cfg.schedule.segment_minutes * 60,
            "site_name": self.cfg.site.name,
            "latitude": self.cfg.site.latitude,
            "longitude": self.cfg.site.longitude,
            "timezone": self.cfg.site.timezone,
        }

        if recording_backend == "sounddevice":
            self._recorder = SounddeviceRecorder(
                device_name_hint=device_record.get("name", ""),
                out_dir=nd / "audio",
                prefix=self.cfg.recording.filename_prefix,
                session_date=session_date,
                sample_rate=self.cfg.recording.sample_rate,
                channels=self.cfg.recording.channels,
                segment_seconds=self.cfg.schedule.segment_minutes * 60,
                on_segment_complete=self._segment_done,
                on_level=lambda db: self._set_status(level_db=db),
                diagnostics_dir=nd / "logs",
                diagnostics_metadata=recorder_metadata,
            )
        else:
            self._recorder = Recorder(
                device_input=device,
                out_dir=nd / "audio",
                prefix=self.cfg.recording.filename_prefix,
                session_date=session_date,
                sample_rate=self.cfg.recording.sample_rate,
                channels=self.cfg.recording.channels,
                bit_depth=self.cfg.recording.bit_depth,
                format_preset=self.cfg.recording.format_preset,
                segment_seconds=self.cfg.schedule.segment_minutes * 60,
                on_segment_complete=self._segment_done,
                on_level=lambda db: self._set_status(level_db=db),
                diagnostics_dir=nd / "logs",
                diagnostics_metadata=recorder_metadata,
            )
        self._add_session_log(
            "recording_started",
            "Recording started.",
            scheduled_starts_at=starts_at.isoformat(timespec="seconds"),
            scheduled_ends_at=ends_at.isoformat(timespec="seconds"),
            output_folder=str(nd),
        )
        self._write_environment_snapshot(nd, datetime.now())

        await self._recorder.start()
        recorder_diagnostics = self._recorder.diagnostics_info()
        self._set_status(recorder_diagnostics=recorder_diagnostics)
        if hasattr(self, "_add_session_log"):
            self._add_session_log(
                "recorder_diagnostics",
                "Recorder diagnostics written.",
                recorder_log=recorder_diagnostics.get("ffmpeg_log", "") or recorder_diagnostics.get("sounddevice_log", ""),
                ffmpeg_log=recorder_diagnostics.get("ffmpeg_log", ""),
                sounddevice_log=recorder_diagnostics.get("sounddevice_log", ""),
                ffmpeg_command=recorder_diagnostics.get("ffmpeg_command_shell", ""),
                device=recorder_metadata,
            )
        self._recording_log_task = asyncio.create_task(self._recording_log_loop())
        self._environment_task = asyncio.create_task(self._environment_loop(nd))
        self._end_task = asyncio.create_task(self._auto_stop_at(ends_at))

    async def _auto_stop_at(self, when: datetime) -> None:
        while True:
            now = datetime.now()
            if now >= when:
                log.info("end of window reached; stopping")
                await self.stop(reason="schedule")
                return
            await asyncio.sleep(min(30.0, max(1.0, (when - now).total_seconds())))

    async def stop(self, reason: str = "user") -> None:
        if self._status["state"] not in ("recording", "awaiting_start", "stopping"):
            return

        self._add_session_log("recording_stopping", f"Recording stopping ({reason}).")
        self._set_status(state="stopping")

        current_task = asyncio.current_task()
        if self._start_task and self._start_task is not current_task:
            self._start_task.cancel()
        if self._end_task and self._end_task is not current_task:
            self._end_task.cancel()
        if self._recording_log_task and self._recording_log_task is not current_task:
            self._recording_log_task.cancel()
        if self._environment_task and self._environment_task is not current_task:
            self._environment_task.cancel()

        if self._recorder:
            await self._recorder.stop()
            self._recorder = None

        self._add_session_log("recording_stopped", f"Recording stopped ({reason}).")
        self._set_status(state="idle")

        if self.cfg.notifications.on_session_end:
            notify("NFC Tools", f"Session ended ({reason}).")

    def _analysis_update(
        self,
        *,
        active: bool | None = None,
        current_file: str | None = None,
        current_analyzer: str | None = None,
        message: str | None = None,
        queue: list[str] | None = None,
        history_event: dict | None = None,
    ) -> None:
        """Update analysis status safely from recorder/analyzer threads."""
        def apply() -> None:
            analysis = dict(self._status.get("analysis") or {})
            analysis.setdefault("active", False)
            analysis.setdefault("current_file", None)
            analysis.setdefault("current_analyzer", None)
            analysis.setdefault("message", "Analysis will start soon after recording stops.")
            analysis.setdefault("queue", [])
            analysis.setdefault("history", [])

            if active is not None:
                analysis["active"] = active
            if current_file is not None:
                analysis["current_file"] = current_file
            if current_analyzer is not None:
                analysis["current_analyzer"] = current_analyzer
            if message is not None:
                analysis["message"] = message
            if queue is not None:
                analysis["queue"] = queue
            if history_event is not None:
                history = [history_event, *analysis.get("history", [])]
                analysis["history"] = history[:12]

            self._set_status(analysis=analysis)

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(apply)
        else:
            apply()

    def _segment_done(self, wav: Path) -> None:
        log.info("segment complete: %s", wav)
        self._add_session_log("segment_completed", "Recording segment completed.", filename=wav.name, size_bytes=wav.stat().st_size if wav.exists() else "")
        self._status["recordings"] = self._status.get("recordings", []) + [wav.name]

        analysis = dict(self._status.get("analysis") or {})
        queue = list(analysis.get("queue", []))
        queue.append(wav.name)

        self._analysis_update(
            active=bool(analysis.get("active")),
            message=f"Queued analysis for {wav.name}",
            queue=queue,
            history_event={
                "time": datetime.now().isoformat(timespec="seconds"),
                "file": wav.name,
                "analyzer": "all",
                "status": "queued",
                "message": "Analysis queued.",
            },
        )
        self._add_session_log("analysis_queued", "Analysis queued for recording segment.", filename=wav.name)
        log.info("analysis queued: %s", wav.name)
        self.on_status(self.status)
        self._pool.submit(self._analyze_one, wav)

    def _analyze_one(self, wav: Path) -> None:
        nd = wav.parent.parent  # audio/ -> night dir
        lock_dir = nd / ".analysis_lock"
        results_dir = nd / "results"
        statuses: dict = {}
        started = datetime.now().isoformat(timespec="seconds")

        log.info("analysis started: %s", wav.name)

        analysis = dict(self._status.get("analysis") or {})
        queue = [q for q in analysis.get("queue", []) if q != wav.name]
        self._analysis_update(
            active=True,
            current_file=wav.name,
            current_analyzer="starting",
            message=f"Starting analysis for {wav.name}",
            queue=queue,
            history_event={
                "time": started,
                "file": wav.name,
                "analyzer": "all",
                "status": "started",
                "message": "Analysis started.",
            },
        )

        try:
            with FileLock(lock_dir, timeout=self.cfg.advanced.lock_timeout_seconds):
                for name in self.cfg.analyzers.enabled:
                    analyzer_started_dt = datetime.now()
                    analyzer_started = analyzer_started_dt.isoformat(timespec="seconds")
                    self._analysis_update(
                        active=True,
                        current_file=wav.name,
                        current_analyzer=name,
                        message=f"Preparing {name} for {wav.name}",
                        history_event={
                            "time": analyzer_started,
                            "file": wav.name,
                            "analyzer": name,
                            "status": "preparing",
                            "message": f"{name} preparing.",
                        },
                    )
                    log.info("analysis preparing: analyzer=%s file=%s", name, wav.name)

                    stop_heartbeat = threading.Event()

                    def heartbeat() -> None:
                        tick = 0
                        while not stop_heartbeat.wait(5):
                            tick += 5
                            msg = f"{name} still running on {wav.name} ({tick}s elapsed)"
                            log.info(
                                "analysis still running: analyzer=%s file=%s elapsed=%ss",
                                name,
                                wav.name,
                                tick,
                            )
                            self._analysis_update(
                                active=True,
                                current_file=wav.name,
                                current_analyzer=name,
                                message=msg,
                            )

                    heartbeat_thread = threading.Thread(
                        target=heartbeat,
                        name=f"nfc-analysis-heartbeat-{name}",
                        daemon=True,
                    )

                    try:
                        plugin = analyzers.get(name)
                        log.info("analysis launching: analyzer=%s file=%s", name, wav.name)
                        self._analysis_update(
                            active=True,
                            current_file=wav.name,
                            current_analyzer=name,
                            message=f"Launching {name} for {wav.name}",
                        )

                        heartbeat_thread.start()
                        result = plugin.run(wav, results_dir / name / wav.stem, self.cfg)
                        stop_heartbeat.set()
                        heartbeat_thread.join(timeout=1)

                        status = "ok" if result.success else "failed"
                        statuses[name] = status

                        message = getattr(result, "message", "") or (
                            f"{name} completed." if result.success else f"{name} failed."
                        )

                        if result.success:
                            log.info(
                                "analysis finished: analyzer=%s file=%s status=ok output=%s",
                                name,
                                wav.name,
                                getattr(result, "output_dir", results_dir / name / wav.stem),
                            )
                        else:
                            log.error(
                                "analysis finished: analyzer=%s file=%s status=failed message=%s",
                                name,
                                wav.name,
                                message,
                            )
                            notify("NFC Tools", f"{name} failed for {wav.name}")

                        self._analysis_update(
                            active=True,
                            current_file=wav.name,
                            current_analyzer=name,
                            message=message,
                            history_event={
                                "time": datetime.now().isoformat(timespec="seconds"),
                                "file": wav.name,
                                "analyzer": name,
                                "status": status,
                                "message": message,
                            },
                        )
                    except Exception as e:  # noqa: BLE001
                        stop_heartbeat.set()
                        if heartbeat_thread.is_alive():
                            heartbeat_thread.join(timeout=1)

                        log.exception("analyzer crashed: analyzer=%s file=%s error=%s", name, wav.name, e)
                        statuses[name] = "error"
                        notify("NFC Tools", f"{name} crashed for {wav.name}")
                        self._analysis_update(
                            active=True,
                            current_file=wav.name,
                            current_analyzer=name,
                            message=f"{name} crashed: {e}",
                            history_event={
                                "time": datetime.now().isoformat(timespec="seconds"),
                                "file": wav.name,
                                "analyzer": name,
                                "status": "error",
                                "message": str(e),
                            },
                        )
                    finally:
                        stop_heartbeat.set()
                        if heartbeat_thread.is_alive():
                            heartbeat_thread.join(timeout=1)

                    log.info("analysis step complete: analyzer=%s file=%s status=%s", name, wav.name, statuses.get(name, "unknown"))
        except LockTimeout:
            log.error("analysis lock timeout: %s", wav.name)
            statuses = {n: "lock_timeout" for n in self.cfg.analyzers.enabled}
            self._analysis_update(
                active=False,
                current_file=wav.name,
                current_analyzer="all",
                message=f"Analysis lock timeout for {wav.name}",
                history_event={
                    "time": datetime.now().isoformat(timespec="seconds"),
                    "file": wav.name,
                    "analyzer": "all",
                    "status": "lock_timeout",
                    "message": "Could not acquire analysis lock.",
                },
            )

        manifest.append(
            nd,
            {
                "session_date": nd.name,
                "recorded_at": "",
                "filename": wav.name,
                "size_bytes": wav.stat().st_size if wav.exists() else 0,
                "started_at": started,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "analyzers": ",".join(self.cfg.analyzers.enabled),
                "statuses": ";".join(f"{k}={v}" for k, v in statuses.items()),
                "notes": "",
            },
        )

        summary = "; ".join(f"{k}={v}" for k, v in statuses.items()) or "no analyzers"
        log.info("analysis batch complete: file=%s statuses=%s", wav.name, summary)
        self._analysis_update(
            active=False,
            current_file=wav.name,
            current_analyzer=None,
            message=f"Analysis complete for {wav.name}: {summary}",
            history_event={
                "time": datetime.now().isoformat(timespec="seconds"),
                "file": wav.name,
                "analyzer": "all",
                "status": "complete",
                "message": summary,
            },
        )


def analyze_existing(wav: Path, cfg: Config) -> dict:
    """Re-run analysis on an existing file. Used by the CLI's `nfc analyze`."""
    from .filenames import parse

    parsed = parse(wav.name)
    if not parsed:
        raise ValueError(f"Unrecognized filename: {wav.name}")

    nd = night_dir(parsed.session_date.isoformat())
    audio_dest = nd / "audio" / wav.name
    if wav.resolve() != audio_dest.resolve():
        with contextlib.suppress(FileExistsError):
            audio_dest.write_bytes(wav.read_bytes())

    s = Session(cfg)
    s._analyze_one(audio_dest)
    return {"session_date": parsed.session_date.isoformat(), "filename": wav.name}
