"""Experimental screening for persistent broad buzz and harmonic line patterns.

This is a review heuristic, not an electrical-fault diagnosis or a general noise
classifier. Thresholds were explored on three noisy and three clean recordings
from one microphone/site, then revised after a normal readiness sample triggered
the original rule. A harmonic screen was added for a missed November sample;
cross-device accuracy is not established.
"""

# Role: Supplies a noise-screening result to readiness checks.
# Dependencies: NumPy computes signal features; ffmpeg_locator supplies the audio decoder.
from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from .ffmpeg_locator import ensure_ffmpeg

SAMPLE_RATE = 8000
DETECTOR = "persistent_buzz_v3"
DECODE_SAMPLE_RATE = 48000


def _harmonic_screen(spectra: np.ndarray, sample_rate: int) -> dict:
    """Find a stationary comb of locally prominent lines, including above 4 kHz.

    Use the weakest contrast/level across all windows so transient sounds cannot
    supply missing harmonics. Fit an integer harmonic series, not just many peaks.
    These conservative engineering thresholds are not an electrical diagnosis.
    """
    upper = min(20000, sample_rate // 2 - 21)
    bins = np.arange(2000, upper + 1)
    thresholds = {"line_contrast_db": 6.0, "line_rms_db": -85.0,
                  "minimum_lines": 12, "minimum_span_hz": 2000,
                  "minimum_aligned_fraction": 0.6, "tolerance_hz": 2.0,
                  "spacing_min_hz": 50.0, "spacing_max_hz": 300.0}
    result = {"review_recommended": False, "thresholds": thresholds,
              "persistent_line_count": 0, "matched_line_count": 0,
              "spacing_hz": None}
    if len(bins) < 3:
        return result
    persistent = np.ones(len(bins), dtype=bool)
    normalization = sample_rate * np.square(np.hanning(sample_rate)).sum()
    for power in spectra:
        neighbors = np.stack([power[bins + offset]
                              for offset in (*range(-20, -4), *range(5, 21))])
        floor = np.maximum(np.median(neighbors, axis=0), 1e-30)
        contrast = 10 * np.log10(np.maximum(power[bins], 1e-30) / floor)
        level = 10 * np.log10(np.maximum(2 * power[bins] / normalization, 1e-30))
        persistent &= (contrast >= 6) & (level >= -85)
    # Collapse adjacent qualifying FFT bins to one line; Hann sidelobes must not
    # inflate the count. Rank by the weakest window's power.
    strength = np.min(spectra[:, bins], axis=0)
    candidates = np.flatnonzero(persistent)
    selected = []
    for index in sorted(candidates, key=lambda i: strength[i], reverse=True):
        if all(abs(index - previous) > 4 for previous in selected):
            selected.append(int(index))
    lines = np.sort(bins[selected])
    result["persistent_line_count"] = len(lines)
    if len(lines) < 12 or np.ptp(lines) < 2000:
        return result
    # A 0.01 Hz grid keeps rounding error below 2 Hz even at the highest harmonic.
    best_count = 0
    for spacing in np.arange(50.0, 300.005, 0.01):
        matched = lines[np.abs(lines - np.rint(lines / spacing) * spacing) <= 2]
        if len(matched) >= max(best_count, 1) and np.ptp(matched) >= 2000:
            best_count = len(matched)
            result["spacing_hz"] = round(float(spacing), 2)
    result["matched_line_count"] = best_count
    result["review_recommended"] = best_count >= 12 and best_count / len(lines) >= 0.6
    return result


def analyze_buzz(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> dict:
    """Screen broad excess and harmonic lines in overlapping one-second windows.

    Compare spectral density with 1.6–2.4 kHz to remove gain dependence. The
    bandwidth gate rejects isolated tones; the target-band level floor rejects
    negligible energy (including FFT leakage from loud low-frequency tones).
    Require a stronger median excess as well: persistent modest coloration alone
    also occurs in normal recordings and is not enough to recommend review.
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
    spectra = []
    for start in starts:
        chunk = x[start:start + size]
        power = np.abs(np.fft.rfft(chunk * taper)) ** 2
        spectra.append(power)
        band = power[target]
        excess = float(10 * np.log10(max(float(band.mean()), 1e-30)
                                    / max(float(power[reference].mean()), 1e-30)))
        # Effective occupied bandwidth: a single sinusoid occupies only a few bins.
        bandwidth = float(band.sum() ** 2 / max(float(np.square(band).sum()), 1e-30))
        rms_db = float(20 * np.log10(max(float(np.sqrt(np.mean(chunk ** 2))), 1e-15)))
        # One-sided FFT power, normalized for the Hann window's energy.
        band_rms_db = float(10 * np.log10(max(
            float(2 * band.sum() / (size * np.square(taper).sum())), 1e-30)))
        windows.append({"start_seconds": start / sample_rate, "excess_db": excess,
                        "bandwidth_hz": bandwidth, "rms_db": rms_db, "band_rms_db": band_rms_db,
                        "matches": excess >= 6.0 and bandwidth >= 80 and band_rms_db >= -60})
    median_excess = float(np.median([w["excess_db"] for w in windows]))
    broad_match = all(w["matches"] for w in windows) and median_excess >= 9.0
    harmonic = _harmonic_screen(np.asarray(spectra), sample_rate)
    return {"detector": DETECTOR, "experimental": True,
            "review_recommended": broad_match or harmonic["review_recommended"],
            "broad_buzz_match": broad_match, "harmonic_screening": harmonic,
            "median_excess_db": median_excess,
            "duration_seconds": len(x) / sample_rate,
            "thresholds": {"excess_db": 6.0, "median_excess_db": 9.0,
                           "bandwidth_hz": 80, "band_rms_db": -60},
            "windows": windows}


async def assess_buzz(path: Path) -> dict:
    """Decode the saved preflight clip with the existing bundled ffmpeg."""
    proc = await asyncio.create_subprocess_exec(
        ensure_ffmpeg(), "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(DECODE_SAMPLE_RATE),
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
    return analyze_buzz(np.frombuffer(raw, dtype="<f4"), DECODE_SAMPLE_RATE)
