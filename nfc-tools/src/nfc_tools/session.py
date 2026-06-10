"""Coordinates a recording session: schedule, recorder, per-segment analysis."""
from __future__ import annotations
import asyncio
import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
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
from .weather import snapshot

log = get("session")


class Session:
	def __init__(self, cfg: Config, on_status: Optional[Callable[[dict], None]] = None):
		self.cfg = cfg
		self.on_status = on_status or (lambda s: None)
		self._recorder: Optional[Recorder] = None
		self._end_task: Optional[asyncio.Task] = None
		self._pool = ThreadPoolExecutor(max_workers=2)
		self._status: dict = {
			"state": "idle", "session_date": None, "started_at": None,
			"ends_at": None, "recordings": [], "level_db": None,
			"weather": None,
		}
		self._loop: Optional[asyncio.AbstractEventLoop] = None

	@property
	def status(self) -> dict:
		return dict(self._status)

	def _set_status(self, **kw) -> None:
		self._status.update(kw)
		try:
			self.on_status(self.status)
		except Exception:  # noqa: BLE001
			pass

	def _resolve_device(self) -> list[str]:
		dev_id = self.cfg.recording.device
		for d in list_input_devices():
			if d["id"] == dev_id:
				return d["ffmpeg_input"]
		raise RuntimeError(
			f"Configured input device '{dev_id}' not found. "
			"Open Settings to choose a different mic."
		)

	async def start(self) -> None:
		if self._status["state"] != "idle":
			raise RuntimeError("Session already running")
		self._loop = asyncio.get_running_loop()

		now = datetime.now()
		win = compute_window(now, self.cfg.schedule.start_time, self.cfg.schedule.end_time)
		nd = night_dir(win.session_date.isoformat())
		device = self._resolve_device()

		weather = snapshot(self.cfg.site.latitude, self.cfg.site.longitude, self.cfg.site.timezone)
		self._set_status(
			state="recording",
			session_date=win.session_date.isoformat(),
			started_at=now.isoformat(timespec="seconds"),
			ends_at=win.ends_at.isoformat(timespec="seconds"),
			recordings=[],
			weather=weather.to_dict(),
		)

		self._recorder = Recorder(
			device_input=device,
			out_dir=nd / "audio",
			prefix=self.cfg.recording.filename_prefix,
			session_date=win.session_date,
			sample_rate=self.cfg.recording.sample_rate,
			channels=self.cfg.recording.channels,
			bit_depth=self.cfg.recording.bit_depth,
			segment_seconds=self.cfg.schedule.segment_minutes * 60,
			on_segment_complete=self._segment_done,
			on_level=lambda db: self._set_status(level_db=db),
		)
		await self._recorder.start()
		self._end_task = asyncio.create_task(self._auto_stop_at(win.ends_at))

	async def _auto_stop_at(self, when: datetime) -> None:
		while True:
			now = datetime.now()
			if now >= when:
				log.info("end of window reached; stopping")
				await self.stop(reason="schedule")
				return
			await asyncio.sleep(min(30.0, (when - now).total_seconds()))

	async def stop(self, reason: str = "user") -> None:
		if self._status["state"] not in ("recording",):
			return
		self._set_status(state="stopping")
		if self._end_task:
			self._end_task.cancel()
		if self._recorder:
			await self._recorder.stop()
		self._set_status(state="idle")
		if self.cfg.notifications.on_session_end:
			notify("NFC Tools", f"Session ended ({reason}).")

	def _segment_done(self, wav: Path) -> None:
		log.info("segment complete: %s", wav)
		self._status["recordings"] = self._status.get("recordings", []) + [wav.name]
		self.on_status(self.status)
		self._pool.submit(self._analyze_one, wav)

	def _analyze_one(self, wav: Path) -> None:
		nd = wav.parent.parent  # audio/ -> night dir
		lock_dir = nd / ".analysis_lock"
		results_dir = nd / "results"
		statuses: dict = {}
		started = datetime.now().isoformat(timespec="seconds")

		try:
			with FileLock(lock_dir, timeout=self.cfg.advanced.lock_timeout_seconds):
				for name in self.cfg.analyzers.enabled:
					try:
						plugin = analyzers.get(name)
						result = plugin.run(wav, results_dir / name / wav.stem, self.cfg)
						statuses[name] = "ok" if result.success else "failed"
						if not result.success:
							notify("NFC Tools", f"{name} failed for {wav.name}")
					except Exception as e:  # noqa: BLE001
						log.exception("analyzer %s crashed: %s", name, e)
						statuses[name] = "error"
						notify("NFC Tools", f"{name} crashed for {wav.name}")
		except LockTimeout:
			log.error("lock timeout for %s", wav)
			statuses = {n: "lock_timeout" for n in self.cfg.analyzers.enabled}

		manifest.append(nd, {
			"session_date": nd.name,
			"recorded_at": "",
			"filename": wav.name,
			"size_bytes": wav.stat().st_size if wav.exists() else 0,
			"started_at": started,
			"finished_at": datetime.now().isoformat(timespec="seconds"),
			"analyzers": ",".join(self.cfg.analyzers.enabled),
			"statuses": ";".join(f"{k}={v}" for k, v in statuses.items()),
			"notes": "",
		})


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
