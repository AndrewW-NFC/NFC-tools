"""Shared sounddevice/CoreAudio helpers for recording and diagnostics."""
from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any


class Float32WavStreamWriter:
    """Streaming little-endian IEEE-float WAV writer.

    Python's stdlib wave module does not write IEEE float WAVs directly. This
    class writes a standard RIFF/WAVE float32 file with placeholder sizes and
    patches them on close. One-hour mono 48 kHz float files are well under the
    4 GB RIFF limit.
    """

    def __init__(self, path: Path, sample_rate: int, channels: int):
        self.path = path
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.frames_written = 0
        self.bytes_written = 0
        self._f = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._f = self.path.open("wb")
        block_align = self.channels * 4
        byte_rate = self.sample_rate * block_align
        self._f.write(b"RIFF")
        self._f.write(struct.pack("<I", 0))
        self._f.write(b"WAVE")
        self._f.write(b"fmt ")
        self._f.write(struct.pack("<IHHIIHH", 16, 3, self.channels, self.sample_rate, byte_rate, block_align, 32))
        self._f.write(b"data")
        self._f.write(struct.pack("<I", 0))
        return self

    def write(self, data) -> int:
        import numpy as np

        if self._f is None:
            raise RuntimeError("WAV writer is not open")
        arr = np.asarray(data, dtype="<f4")
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        if arr.shape[1] < self.channels:
            raise ValueError(f"Expected {self.channels} channel(s), got {arr.shape[1]}")
        if arr.shape[1] > self.channels:
            arr = arr[:, : self.channels]
        payload = arr.astype("<f4", copy=False).tobytes()
        self._f.write(payload)
        frames = int(arr.shape[0])
        self.frames_written += frames
        self.bytes_written += len(payload)
        return frames

    def close(self) -> None:
        if self._f is None:
            return
        riff_size = 36 + self.bytes_written
        data_size = self.bytes_written
        self._f.seek(4)
        self._f.write(struct.pack("<I", riff_size))
        self._f.seek(40)
        self._f.write(struct.pack("<I", data_size))
        self._f.close()
        self._f = None

    def __exit__(self, exc_type, exc, tb):
        self.close()


def write_float32_wav(path: Path, samples, sample_rate: int, channels: int) -> None:
    with Float32WavStreamWriter(path, sample_rate, channels) as writer:
        writer.write(samples)


def db(value: float) -> float:
    return 20 * math.log10(max(float(value), 1e-12))


def safe_rms(samples) -> float:
    import numpy as np

    arr = np.asarray(samples, dtype="float64")
    if arr.size == 0:
        return 0.0
    return float(math.sqrt(float(np.mean(arr * arr))))


def level_metrics(samples) -> dict:
    import numpy as np

    arr = np.asarray(samples, dtype="float64")
    if arr.size:
        abs_arr = np.abs(arr)
        peak = float(np.max(abs_arr))
        rms = safe_rms(arr)
        near_full = float(np.mean(abs_arr >= 0.999))
    else:
        peak = 0.0
        rms = 0.0
        near_full = 0.0

    rms_db = db(rms)
    return {
        "rms": rms,
        "peak": peak,
        "rms_db": rms_db,
        "peak_db": db(peak),
        "level_db": rms_db,
        "near_full_scale_fraction": near_full,
    }


def device_summary(sd) -> list[dict[str, Any]]:
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


def choose_input_device(sd, selected_name: str | None) -> int | None:
    devices = sd.query_devices()
    name = (selected_name or "").strip().lower()
    candidates: list[int] = []

    for idx, dev in enumerate(devices):
        if int(dev.get("max_input_channels", 0) or 0) <= 0:
            continue
        candidates.append(idx)
        dev_name = str(dev.get("name", "")).strip().lower()
        if name and (name in dev_name or dev_name in name):
            return idx

    try:
        default_input = sd.default.device[0]
        if default_input is not None and int(default_input) >= 0:
            return int(default_input)
    except Exception:  # noqa: BLE001
        pass

    return candidates[0] if candidates else None
