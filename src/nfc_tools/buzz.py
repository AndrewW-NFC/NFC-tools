"""Experimental screening for the persistent broad buzz in field examples.

This is a review heuristic, not an electrical-fault diagnosis or a general noise
classifier. Thresholds were explored on three noisy and three clean recordings
from one microphone/site; cross-device accuracy is not established.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from .ffmpeg_locator import ensure_ffmpeg

SAMPLE_RATE = 8000


def analyze_buzz(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict:
    """Require broad 0.8–1.4 kHz excess in *every* overlapping one-second window.

    Compare spectral density with 1.6–2.4 kHz to remove gain dependence. The
    bandwidth gate rejects isolated tones; the level floor rejects near silence.
    Include a final window ending at the last sample, even for fractional lengths.
    """
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or sample_rate < 4800 or len(x) < 2 * sample_rate or not np.isfinite(x).all():
        raise ValueError("Buzz screening needs at least two seconds of finite mono audio")
    size = sample_rate
    starts = sorted(set(range(0, len(x) - size + 1, size // 4)) | {len(x) - size})
    taper = np.hanning(size)
    frequencies = np.fft.rfftfreq(size, 1 / sample_rate)
    target = (frequencies >= 800) & (frequencies < 1400)
    reference = (frequencies >= 1600) & (frequencies < 2400)
    windows = []
    for start in starts:
        chunk = x[start:start + size]
        power = np.abs(np.fft.rfft(chunk * taper)) ** 2
        band = power[target]
        excess = float(10 * np.log10(max(float(band.mean()), 1e-30)
                                    / max(float(power[reference].mean()), 1e-30)))
        # Effective occupied bandwidth: a single sinusoid occupies only a few bins.
        bandwidth = float(band.sum() ** 2 / max(float(np.square(band).sum()), 1e-30))
        rms_db = float(20 * np.log10(max(float(np.sqrt(np.mean(chunk ** 2))), 1e-15)))
        windows.append({"start_seconds": start / sample_rate, "excess_db": excess,
                        "bandwidth_hz": bandwidth, "rms_db": rms_db,
                        "matches": excess >= 6.0 and bandwidth >= 80 and rms_db >= -60})
    return {"detector": "persistent_broad_buzz_v1", "experimental": True,
            "review_recommended": all(w["matches"] for w in windows),
            "duration_seconds": len(x) / sample_rate,
            "thresholds": {"excess_db": 6.0, "bandwidth_hz": 80, "rms_db": -60},
            "windows": windows}


async def assess_buzz(path: Path) -> dict:
    """Decode the saved preflight clip with the existing bundled ffmpeg."""
    proc = await asyncio.create_subprocess_exec(
        ensure_ffmpeg(), "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SAMPLE_RATE),
        "-f", "f32le", "-", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        raw, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
    except BaseException:
        if proc.returncode is None:
            proc.kill()
        await proc.wait()
        raise
    if proc.returncode:
        raise ValueError("Could not decode sample for buzz screening")
    return analyze_buzz(np.frombuffer(raw, dtype="<f4"))
