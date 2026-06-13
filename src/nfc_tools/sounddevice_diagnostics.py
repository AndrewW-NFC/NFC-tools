"""Sounddevice / PortAudio recording diagnostics.

This module exists to compare a non-ffmpeg macOS/CoreAudio capture path against
ffmpeg's avfoundation path when troubleshooting recurring short spikes.
"""
from __future__ import annotations

import asyncio
import json
import math
import struct
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def _write_float32_wav(path: Path, samples, sample_rate: int, channels: int) -> None:
    """Write a simple little-endian IEEE float WAV without extra dependencies."""
    import numpy as np

    arr = np.asarray(samples, dtype="<f4")
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.shape[1] != channels:
        arr = arr[:, :channels]
    data = arr.astype("<f4", copy=False).tobytes()
    block_align = channels * 4
    byte_rate = sample_rate * block_align

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + len(data)))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 3, channels, sample_rate, byte_rate, block_align, 32))
        f.write(b"data")
        f.write(struct.pack("<I", len(data)))
        f.write(data)


def _safe_rms(samples) -> float:
    import numpy as np

    arr = np.asarray(samples, dtype="float64")
    if arr.size == 0:
        return 0.0
    return float(math.sqrt(float(np.mean(arr * arr))))


def _device_summary(sd) -> list[dict[str, Any]]:
    rows = []
    for idx, dev in enumerate(sd.query_devices()):
        rows.append({
            "index": idx,
            "name": str(dev.get("name", "")),
            "max_input_channels": int(dev.get("max_input_channels", 0) or 0),
            "max_output_channels": int(dev.get("max_output_channels", 0) or 0),
            "default_samplerate": float(dev.get("default_samplerate", 0) or 0),
        })
    return rows


def _choose_input_device(sd, selected_name: str | None) -> int | None:
    devices = sd.query_devices()
    name = (selected_name or "").strip().lower()
    candidates = []
    for idx, dev in enumerate(devices):
        if int(dev.get("max_input_channels", 0) or 0) <= 0:
            continue
        candidates.append(idx)
        dev_name = str(dev.get("name", "")).lower()
        if name and (name in dev_name or dev_name in name):
            return idx

    try:
        default_input = sd.default.device[0]
        if default_input is not None and int(default_input) >= 0:
            return int(default_input)
    except Exception:
        pass

    return candidates[0] if candidates else None


def _record_sync(out_path: Path, *, seconds: int, sample_rate: int, channels: int, selected_name: str | None) -> dict:
    import numpy as np
    import sounddevice as sd

    started_at = datetime.now().isoformat(timespec="seconds")
    devices = _device_summary(sd)
    device_index = _choose_input_device(sd, selected_name)
    if device_index is None:
        raise RuntimeError("No PortAudio/sounddevice input device was found.")

    frames = int(seconds * sample_rate)
    recording = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        device=device_index,
        blocking=True,
    )
    sd.wait()
    arr = np.asarray(recording, dtype="float32")
    _write_float32_wav(out_path, arr, sample_rate=sample_rate, channels=channels)

    peak = float(np.max(np.abs(arr))) if arr.size else 0.0
    rms = _safe_rms(arr)
    chosen = devices[device_index] if 0 <= device_index < len(devices) else {"index": device_index}
    return {
        "started_at": started_at,
        "backend": "sounddevice/PortAudio/CoreAudio",
        "selected_name_hint": selected_name or "",
        "chosen_device_index": device_index,
        "chosen_device": chosen,
        "all_devices": devices,
        "duration_seconds": seconds,
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_format": "float32",
        "frames_requested": frames,
        "frames_recorded": int(arr.shape[0]) if arr.ndim else 0,
        "peak_abs": peak,
        "rms": rms,
        "near_full_scale_fraction": float(np.mean(np.abs(arr) >= 0.999)) if arr.size else 0.0,
    }


async def record_sounddevice_test(
    out_path: Path,
    *,
    seconds: int = 10,
    sample_rate: int = 48000,
    channels: int = 1,
    selected_name: str | None = None,
) -> dict:
    """Record a short non-ffmpeg diagnostic clip through sounddevice."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    log_path = out_path.with_suffix(".sounddevice.log")
    try:
        meta = await asyncio.to_thread(
            _record_sync,
            out_path,
            seconds=seconds,
            sample_rate=sample_rate,
            channels=channels,
            selected_name=selected_name,
        )
        header = {
            "ok": True,
            "note": "Non-ffmpeg diagnostic: sounddevice/PortAudio/CoreAudio -> 48 kHz -> 32-bit float WAV.",
            "metadata": meta,
            "wav_path": str(out_path),
        }
        log_path.write_text("NFC Tools sounddevice/CoreAudio raw recording test diagnostics\n" + json.dumps(header, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "ok": True,
            "variant": "sounddevice_coreaudio_float_48k",
            "variant_description": "sounddevice/CoreAudio 48 kHz 32-bit float WAV; no ffmpeg/avfoundation path.",
            "wav_path": str(out_path),
            "wav_name": out_path.name,
            "log_path": str(log_path),
            "log_name": log_path.name,
            "size_bytes": out_path.stat().st_size if out_path.exists() else 0,
            "metadata": meta,
        }
    except Exception as exc:  # noqa: BLE001
        header = {
            "ok": False,
            "error": str(exc),
            "note": "Install/repair may require: python -m pip install -e . and macOS microphone permission for the Terminal/Python process.",
            "wav_path": str(out_path),
        }
        log_path.write_text("NFC Tools sounddevice/CoreAudio raw recording test diagnostics\n" + json.dumps(header, indent=2, sort_keys=True), encoding="utf-8")
        return {
            "ok": False,
            "variant": "sounddevice_coreaudio_float_48k",
            "error": str(exc),
            "wav_path": str(out_path),
            "wav_name": out_path.name,
            "log_path": str(log_path),
            "log_name": log_path.name,
            "size_bytes": out_path.stat().st_size if out_path.exists() else 0,
        }


def _db(value: float) -> float:
    return 20 * math.log10(max(float(value), 1e-12))


def _level_metrics(samples) -> dict:
    import numpy as np

    arr = np.asarray(samples, dtype="float64")
    if arr.size:
        abs_arr = np.abs(arr)
        peak = float(np.max(abs_arr))
        rms = _safe_rms(arr)
        near_full = float(np.mean(abs_arr >= 0.999))
    else:
        peak = 0.0
        rms = 0.0
        near_full = 0.0

    return {
        "rms": rms,
        "peak": peak,
        "rms_db": _db(rms),
        "peak_db": _db(peak),
        "level_db": _db(rms),
        "near_full_scale_fraction": near_full,
    }


def _measure_levels_sync(*, seconds: float, sample_rate: int, channels: int, selected_name: str | None) -> dict:
    import sounddevice as sd

    devices = _device_summary(sd)
    device_index = _choose_input_device(sd, selected_name)
    if device_index is None:
        raise RuntimeError("No PortAudio/sounddevice input device was found.")

    frames = max(1, int(float(seconds) * int(sample_rate)))
    recording = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        device=device_index,
        blocking=True,
    )
    sd.wait()

    chosen = devices[device_index] if 0 <= device_index < len(devices) else {"index": device_index}
    return {
        "source": "sounddevice_coreaudio",
        "recording": False,
        "sample_rate": sample_rate,
        "channels": channels,
        "device_index": device_index,
        "device_name": chosen.get("name", ""),
        **_level_metrics(recording),
    }


async def measure_sounddevice_levels(
    *,
    seconds: float = 0.35,
    sample_rate: int = 48000,
    channels: int = 1,
    selected_name: str | None = None,
) -> dict:
    """Measure current input level through the same sounddevice/CoreAudio family used for macOS recording."""
    return await asyncio.to_thread(
        _measure_levels_sync,
        seconds=seconds,
        sample_rate=sample_rate,
        channels=channels,
        selected_name=selected_name,
    )


class SounddevicePreviewMeter:
    """Persistent CoreAudio preview stream for dashboard standby metering."""

    def __init__(self, *, idle_timeout: float = 8.0):
        self.idle_timeout = idle_timeout
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._started_event = threading.Event()
        self._sample_event = threading.Event()
        self._startup_error: Exception | None = None
        self._latest: dict | None = None
        self._config: tuple[int, int, str] | None = None
        self._last_request = 0.0

    def measure(self, *, sample_rate: int, channels: int, selected_name: str | None = None) -> dict:
        config = (int(sample_rate), int(channels), selected_name or "")
        self._ensure_stream(config)

        if not self._started_event.wait(5):
            self.stop()
            raise RuntimeError("sounddevice/CoreAudio preview did not start within 5 seconds.")

        with self._lock:
            error = self._startup_error
        if error:
            self.stop()
            raise RuntimeError(f"sounddevice/CoreAudio preview failed to start: {error}") from error

        self._sample_event.wait(0.75)
        with self._lock:
            if self._latest:
                return dict(self._latest)

        sample_rate, channels, selected_name = config
        return {
            "source": "sounddevice_coreaudio_preview",
            "recording": False,
            "sample_rate": sample_rate,
            "channels": channels,
            "device_index": None,
            "device_name": selected_name,
            "rms": 0.0,
            "peak": 0.0,
            "rms_db": -120.0,
            "peak_db": -120.0,
            "level_db": -120.0,
            "near_full_scale_fraction": 0.0,
            "warming_up": True,
        }

    def stop(self) -> None:
        with self._lock:
            thread = self._thread
            self._stop_event.set()

        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)

        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _ensure_stream(self, config: tuple[int, int, str]) -> None:
        restart_thread: threading.Thread | None = None
        with self._lock:
            self._last_request = time.monotonic()
            if self._thread and self._thread.is_alive() and self._config == config:
                return

            restart_thread = self._thread
            self._stop_event.set()

        if restart_thread and restart_thread.is_alive() and restart_thread is not threading.current_thread():
            restart_thread.join(timeout=2)

        with self._lock:
            self._config = config
            self._latest = None
            self._startup_error = None
            self._stop_event = threading.Event()
            self._started_event = threading.Event()
            self._sample_event = threading.Event()
            self._thread = threading.Thread(
                target=self._run,
                args=(config,),
                name="nfc-sounddevice-preview-meter",
                daemon=True,
            )
            self._thread.start()

    def _run(self, config: tuple[int, int, str]) -> None:
        sample_rate, channels, selected_name = config
        try:
            import numpy as np
            import sounddevice as sd

            devices = _device_summary(sd)
            device_index = _choose_input_device(sd, selected_name)
            if device_index is None:
                raise RuntimeError("No PortAudio/sounddevice input device was found.")

            chosen = devices[device_index] if 0 <= device_index < len(devices) else {"index": device_index}

            def callback(indata, frames, time_info, status):  # noqa: ANN001
                metrics = _level_metrics(np.asarray(indata, dtype="float32"))
                payload = {
                    "source": "sounddevice_coreaudio_preview",
                    "recording": False,
                    "sample_rate": sample_rate,
                    "channels": channels,
                    "device_index": device_index,
                    "device_name": chosen.get("name", ""),
                    "stream_status": str(status) if status else "",
                    **metrics,
                }
                with self._lock:
                    self._latest = payload
                    self._sample_event.set()

            with sd.InputStream(
                samplerate=sample_rate,
                channels=channels,
                dtype="float32",
                device=device_index,
                blocksize=max(256, int(sample_rate * 0.05)),
                callback=callback,
            ):
                self._started_event.set()
                while not self._stop_event.wait(0.25):
                    with self._lock:
                        idle_for = time.monotonic() - self._last_request
                    if idle_for > self.idle_timeout:
                        break
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._startup_error = exc
                self._started_event.set()
        finally:
            with self._lock:
                if self._thread is threading.current_thread():
                    self._thread = None


_preview_meter = SounddevicePreviewMeter()


async def measure_sounddevice_preview_level(
    *,
    sample_rate: int = 48000,
    channels: int = 1,
    selected_name: str | None = None,
) -> dict:
    """Measure input level through a persistent standby preview stream."""
    return await asyncio.to_thread(
        _preview_meter.measure,
        sample_rate=sample_rate,
        channels=channels,
        selected_name=selected_name,
    )
