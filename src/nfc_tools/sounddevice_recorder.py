"""sounddevice / PortAudio / CoreAudio recording backend.

This backend is preferred on macOS because testing showed the ffmpeg
avfoundation path introduced recurring short spikes while sounddevice/CoreAudio
produced clean 48 kHz float audio with the same hardware.
"""
from __future__ import annotations

import asyncio
import json
import queue
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .filenames import make, next_index_for_directory
from .logging_setup import get
from .sounddevice_common import Float32WavStreamWriter, choose_input_device, device_summary, level_metrics

log = get("sounddevice_recorder")


class SounddeviceRecorder:
    """Segmenting recorder that bypasses ffmpeg/avfoundation on macOS."""

    def __init__(
        self,
        *,
        device_name_hint: str | None,
        out_dir: Path,
        prefix: str,
        session_date: date,
        sample_rate: int = 48000,
        channels: int = 1,
        segment_seconds: int = 3600,
        segment_seconds_for_start: Optional[Callable[[datetime, int], int]] = None,
        period_for_start: Optional[Callable[[datetime], str]] = None,
        on_segment_complete: Optional[Callable[[Path], None]] = None,
        on_level: Optional[Callable[[float], None]] = None,
        diagnostics_dir: Optional[Path] = None,
        diagnostics_metadata: Optional[dict] = None,
        timezone_name: str | None = None,
    ):
        self.device_name_hint = device_name_hint or ""
        self.out_dir = out_dir
        self.prefix = prefix
        self.session_date = session_date
        self.sample_rate = int(sample_rate or 48000)
        self.channels = int(channels or 1)
        self.segment_seconds = int(segment_seconds or 3600)
        self.segment_seconds_for_start = segment_seconds_for_start
        self.period_for_start = period_for_start
        self.on_segment_complete = on_segment_complete
        self.on_level = on_level
        self.diagnostics_dir = diagnostics_dir
        self.diagnostics_metadata = diagnostics_metadata or {}
        self.timezone_name = timezone_name

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._queue: queue.Queue = queue.Queue()
        self._completed_paths: set[Path] = set()
        self._current_path: Path | None = None
        self._next_segment_index: int | None = None
        self._diagnostics_path: Path | None = None
        self._metadata: dict = {}
        self._started_event = threading.Event()
        self._first_sample_event = threading.Event()
        self._startup_error: Exception | None = None
        self._chunks_seen = 0

    def _segment_path(self, started_at: datetime) -> Path:
        period = self.period_for_start(started_at) if self.period_for_start else "nfc"
        filename_started_at = started_at.replace(microsecond=0)
        if self._next_segment_index is None:
            self._next_segment_index = next_index_for_directory(self.out_dir)
        segment_index = self._next_segment_index
        self._next_segment_index += 1
        return self.out_dir / make(
            self.prefix,
            self.session_date,
            filename_started_at,
            period=period,
            index=segment_index,
        )

    def _segment_frames(self, started_at: datetime) -> int:
        seconds = self.segment_seconds
        if self.segment_seconds_for_start:
            seconds = self.segment_seconds_for_start(started_at, self.segment_seconds)
        return max(1, self.sample_rate * int(seconds))

    def _write_diag(self, event: str, **data) -> None:
        if not self._diagnostics_path:
            return
        payload = {"time": datetime.now().isoformat(timespec="seconds"), "event": event, **data}
        try:
            with self._diagnostics_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, sort_keys=True, default=str) + "\n")
        except Exception:  # noqa: BLE001
            pass

    def _open_diagnostics(self) -> None:
        if not self.diagnostics_dir:
            return
        self.diagnostics_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._diagnostics_path = self.diagnostics_dir / f"sounddevice_recording_{stamp}.log"
        header = {
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "backend": "sounddevice/PortAudio/CoreAudio",
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "device_name_hint": self.device_name_hint,
            "metadata": self.diagnostics_metadata,
        }
        with self._diagnostics_path.open("w", encoding="utf-8") as f:
            f.write("NFC Tools sounddevice recording diagnostics\n")
            f.write(json.dumps(header, indent=2, sort_keys=True, default=str))
            f.write("\n\n--- events ---\n")

    def diagnostics_info(self) -> dict:
        return {
            "recording_backend": "sounddevice_coreaudio",
            "sounddevice_log": str(self._diagnostics_path) if self._diagnostics_path else "",
            "metadata": dict(self._metadata or self.diagnostics_metadata),
        }

    def _mark_segment_complete(self, wav_path: Path) -> None:
        wav_path = wav_path.resolve()
        if wav_path in self._completed_paths:
            return
        if not wav_path.exists() or wav_path.stat().st_size == 0:
            log.warning("sounddevice segment skipped because file is missing or empty: %s", wav_path)
            return
        self._completed_paths.add(wav_path)
        self._write_diag("segment_complete", path=str(wav_path), size_bytes=wav_path.stat().st_size)
        if self.on_segment_complete:
            try:
                self.on_segment_complete(wav_path)
            except Exception as e:  # noqa: BLE001
                log.exception("segment callback failed: %s", e)

    async def start(self) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self._stop_event.clear()
        self._started_event.clear()
        self._first_sample_event.clear()
        self._startup_error = None
        self._chunks_seen = 0
        self._open_diagnostics()
        self._thread = threading.Thread(target=self._run, name="nfc-sounddevice-recorder", daemon=True)
        self._thread.start()
        self._write_diag("thread_started")
        started = await asyncio.to_thread(self._started_event.wait, 10)
        if not started:
            self._stop_event.set()
            self._write_diag("startup_timeout", timeout_seconds=10)
            if self._thread and self._thread.is_alive():
                await asyncio.to_thread(self._thread.join, 2)
            self._thread = None
            raise RuntimeError("sounddevice/CoreAudio recorder did not start within 10 seconds.")
        if self._startup_error:
            error = self._startup_error
            if self._thread and self._thread.is_alive():
                await asyncio.to_thread(self._thread.join, 2)
            self._thread = None
            raise RuntimeError(f"sounddevice/CoreAudio recorder failed to start: {error}") from error

        first_sample = await asyncio.to_thread(self._first_sample_event.wait, 10)
        if not first_sample:
            self._stop_event.set()
            self._write_diag("no_audio_samples", timeout_seconds=10)
            if self._thread and self._thread.is_alive():
                await asyncio.to_thread(self._thread.join, 5)
            self._thread = None
            raise RuntimeError(
                "sounddevice/CoreAudio stream started, but no audio samples arrived within 10 seconds. "
                "Check microphone permission, the selected input device, and whether the mic is still connected."
            )

    async def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            await asyncio.to_thread(self._thread.join, 15)
        self._thread = None
        self._write_diag("stopped")

    def _run(self) -> None:
        segment_frames = max(1, self.sample_rate * self.segment_seconds)
        frames_in_segment = 0
        writer: Float32WavStreamWriter | None = None

        try:
            import numpy as np
            import sounddevice as sd

            devices = device_summary(sd)
            device_index = choose_input_device(sd, self.device_name_hint)
            if device_index is None:
                raise RuntimeError("No PortAudio/sounddevice input device was found.")

            chosen = devices[device_index] if 0 <= device_index < len(devices) else {"index": device_index}
            self._metadata = {
                **self.diagnostics_metadata,
                "backend": "sounddevice_coreaudio",
                "sounddevice_device_index": device_index,
                "sounddevice_device": chosen,
                "all_sounddevice_devices": devices,
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "sample_format": "float32",
            }
            self._write_diag("device_selected", chosen_device=chosen, all_devices=devices)

            def callback(indata, frames, time_info, status):  # noqa: ANN001
                if status:
                    self._write_diag("stream_status", status=str(status))
                self._queue.put(np.asarray(indata, dtype="float32").copy())
                self._chunks_seen += 1
                self._first_sample_event.set()

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                device=device_index,
                callback=callback,
            ):
                self._write_diag("stream_started")
                segment_started_at = self._now()
                segment_frames = self._segment_frames(segment_started_at)
                self._current_path = self._segment_path(segment_started_at)
                writer = Float32WavStreamWriter(self._current_path, self.sample_rate, self.channels)
                writer.__enter__()
                self._write_diag("segment_opened", path=str(self._current_path), segment_frames=segment_frames)
                self._started_event.set()

                while not self._stop_event.is_set() or not self._queue.empty():
                    try:
                        chunk = self._queue.get(timeout=0.25)
                    except queue.Empty:
                        continue

                    if writer is None:
                        segment_started_at = self._now()
                        segment_frames = self._segment_frames(segment_started_at)
                        self._current_path = self._segment_path(segment_started_at)
                        writer = Float32WavStreamWriter(self._current_path, self.sample_rate, self.channels)
                        writer.__enter__()
                        frames_in_segment = 0
                        self._write_diag("segment_opened", path=str(self._current_path), segment_frames=segment_frames)

                    frames_written = writer.write(chunk)
                    frames_in_segment += frames_written

                    if self.on_level:
                        try:
                            self.on_level(level_metrics(chunk))
                        except Exception:  # noqa: BLE001
                            pass

                    if frames_in_segment >= segment_frames:
                        completed = self._current_path
                        written = writer.frames_written
                        writer.close()
                        writer = None
                        frames_in_segment = 0
                        if completed and written > 0:
                            self._mark_segment_complete(completed)

                self._write_diag("stop_event_seen")
        except Exception as exc:  # noqa: BLE001
            if not self._started_event.is_set():
                self._startup_error = exc
                self._started_event.set()
            self._write_diag("error", error=str(exc))
            log.exception("sounddevice recorder failed: %s", exc)
        finally:
            if writer is not None:
                completed = self._current_path
                written = writer.frames_written
                writer.close()
                if completed and written > 0:
                    self._mark_segment_complete(completed)
                elif completed and completed.exists():
                    self._write_diag(
                        "segment_discarded",
                        path=str(completed),
                        frames_written=written,
                        chunks_seen=self._chunks_seen,
                        reason="no_audio_frames_written",
                    )
                    try:
                        completed.unlink()
                    except Exception:  # noqa: BLE001
                        pass
            self._write_diag("thread_exiting")
    def _now(self) -> datetime:
        if self.timezone_name:
            try:
                return datetime.now(ZoneInfo(self.timezone_name))
            except ZoneInfoNotFoundError:
                pass
        return datetime.now()
