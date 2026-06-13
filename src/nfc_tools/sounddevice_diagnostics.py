"""Sounddevice / PortAudio recording diagnostics.

This module exists to compare a non-ffmpeg macOS/CoreAudio capture path against
ffmpeg's avfoundation path when troubleshooting recurring short spikes.
"""
from __future__ import annotations

import asyncio
import json
import math
import struct
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
