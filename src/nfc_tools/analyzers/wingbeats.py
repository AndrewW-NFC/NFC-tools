"""Experimental pulse-train screening; WING means possible wingbeats, not an ID."""
from __future__ import annotations

import csv
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..ffmpeg_locator import ensure_ffmpeg
from .base import AnalyzerResult, register
from .wingbeat_accompaniment import (
    ANALYSIS_RATE,
    _smooth,
    accompaniment_features,
    screen_accompaniment,
)

SAMPLE_RATE = 8000  # Legacy broadband callers; the plugin decodes at ANALYSIS_RATE.
WINDOW_SECONDS = 2
HOP_SECONDS = 1
PULSE_BANDS = ((150, 600), (600, 1200), (1200, 2000), (2000, 3001))


@dataclass(frozen=True)
class Candidate:
    start: float
    end: float
    periodicity: float  # Similarity of repeated pulses, NOT a probability.


@dataclass(frozen=True)
class WindowFeatures:
    spectral_flatness: float
    modulation: float
    periodicity: float
    repeat_periodicity: float
    pulse_count: int
    peak_envelope: float
    coherent_bands: int
    band_energy_fraction: float


def window_features(
    samples: np.ndarray, sample_rate: int = SAMPLE_RATE, *, detrend: bool = True,
) -> WindowFeatures | None:
    """Measure a window; detrend=False is only for historical evaluation.

    Scores are not probabilities. Remove 510 ms loudness trends before rhythm
    and cross-band synchrony checks so gradual wind swells cannot supply their
    common baseline. Preserve the raw envelope for amplitude/contrast gates.
    """
    if len(samples) < sample_rate or not np.isfinite(samples).all():
        return None
    frame_size = sample_rate * 32 // 1000
    frames = np.lib.stride_tricks.sliding_window_view(samples, frame_size)[::sample_rate // 100]
    power = np.abs(np.fft.rfft(frames * np.hanning(frame_size), axis=1)) ** 2
    frequencies = np.fft.rfftfreq(frame_size, 1 / sample_rate)
    band = power[:, (frequencies >= 150) & (frequencies <= 3000)]
    # Assess individual frames: averaging spectra first makes a sweeping tone
    # look broadband, even though it is narrowband at every instant.
    frame_flatness = np.exp(np.log(band + 1e-20).mean(axis=1)) / (band.mean(axis=1) + 1e-20)
    envelope = np.sqrt(band.sum(axis=1))
    # 30 ms smoothing reduces frame-to-frame noise without erasing the pulses.
    envelope = np.convolve(envelope, np.ones(3) / 3, mode="valid")
    loud = envelope >= np.percentile(envelope, 75)
    flatness = float(np.median(frame_flatness[1:-1][loud]))
    # High-frequency whistles can leave tiny, apparently broadband sidelobes
    # below 3 kHz. Do not treat that leakage as a separate low-band signal.
    energy_fraction = band.sum(axis=1) / (power.sum(axis=1) + 1e-20)
    band_energy_fraction = float(np.median(energy_fraction[1:-1][loud]))
    low, high = np.percentile(envelope, [10, 90])
    modulation = float((high - low) / (high + 1e-20))
    centered = envelope - (_smooth(envelope, 51) if detrend else envelope.mean())
    correlations = [0.0]
    for lag in range(1, min(102, len(centered) // 2)):
        left, right = centered[:-lag], centered[lag:]
        denom = np.linalg.norm(left) * np.linalg.norm(right)
        correlations.append(float(np.dot(left, right) / denom) if denom else 0.0)
    # A local autocorrelation peak plus repetition at twice the lag provides
    # stronger evidence of a pulse train than slow loudness variation alone.
    lags = [lag for lag in range(5, min(51, len(centered) // 4))
            if correlations[lag] > correlations[lag - 1]
            and correlations[lag] >= correlations[lag + 1]]
    best = max(lags, key=lambda lag: correlations[lag], default=None)
    # Broadband background can make a pulsed tone pass spectral flatness.
    # Require the *modulation* to occur together across separate frequency bands,
    # at the same period selected from the full-band envelope.
    coherent_bands = 0
    if best is not None:
        for lower, upper in PULSE_BANDS:
            band_envelope = np.sqrt(power[:, (frequencies >= lower) & (frequencies < upper)].sum(axis=1))
            band_envelope = np.convolve(band_envelope, np.ones(3) / 3, mode="valid")
            band_low, band_high = np.percentile(band_envelope, [10, 90])
            band_modulation = (band_high - band_low) / (band_high + 1e-20)
            band_centered = band_envelope - (_smooth(band_envelope, 51) if detrend else band_envelope.mean())
            denom = np.linalg.norm(band_centered) * np.linalg.norm(centered)
            coherence = float(np.dot(band_centered, centered) / denom) if denom else 0.0
            left, right = band_centered[:-best], band_centered[best:]
            denom = np.linalg.norm(left) * np.linalg.norm(right)
            repetition = float(np.dot(left, right) / denom) if denom else 0.0
            if coherence >= 0.60 and repetition >= 0.35 and band_modulation >= 0.15:
                coherent_bands += 1
    above = envelope > low + 0.6 * (high - low)
    pulses = int(np.count_nonzero(above[1:] & ~above[:-1]) + int(above[0]))
    return WindowFeatures(
        flatness, modulation, correlations[best] if best else 0.0,
        correlations[2 * best] if best else 0.0, pulses, float(envelope.max()), coherent_bands, band_energy_fraction,
    )


def screen_window(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float | None:
    """Screen for broadband pulses or pulse-linked spectral accompaniment.

    24 kHz input enables the accompaniment path; 8 kHz callers retain the
    broadband screen. Repetition gates cover approximately 2–20 Hz.

    Provisional engineering cutoffs: not a trained or calibrated classifier.
    Background sound can reduce modulation, so accept moderate contrast only
    when the envelope repeats at both one and two pulse periods.
    """
    features = window_features(samples, sample_rate)
    if features is None:
        return None
    if (features.peak_envelope < 1e-4 or features.spectral_flatness < 0.12
            or features.modulation < 0.25 or features.periodicity < 0.6
            or features.repeat_periodicity < 0.35 or features.pulse_count < 4
            or features.coherent_bands < 3
            or (sample_rate == ANALYSIS_RATE and features.band_energy_fraction < 1e-4)):
        if sample_rate == ANALYSIS_RATE:
            return screen_accompaniment(accompaniment_features(samples))
        return None
    return features.periodicity


def detect_stream(stream, sample_rate: int = SAMPLE_RATE) -> list[Candidate]:
    """Read mono float32 PCM in overlapping windows, bounded audio memory."""
    window_bytes = sample_rate * WINDOW_SECONDS * 4
    hop_bytes = sample_rate * HOP_SECONDS * 4
    buffer = b""
    offset = 0.0
    candidates: list[Candidate] = []
    while True:
        chunk = stream.read(window_bytes - len(buffer))
        buffer += chunk
        eof = not chunk
        if len(buffer) < window_bytes and not eof:
            continue
        if len(buffer) % 4:
            raise ValueError("Truncated decoded audio")
        samples = np.frombuffer(buffer, dtype="<f4")
        score = screen_window(samples, sample_rate)
        if score is not None:
            end = offset + len(samples) / sample_rate
            if candidates and offset <= candidates[-1].end:
                previous = candidates.pop()
                candidates.append(Candidate(previous.start, end, max(previous.periodicity, score)))
            else:
                candidates.append(Candidate(offset, end, score))
        if eof:
            break
        buffer = buffer[hop_bytes:]
        offset += HOP_SECONDS
    return candidates


class WingbeatsPlugin:
    name = "wingbeats"

    def run(self, wav_path: Path, output_dir: Path, cfg) -> AnalyzerResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            # FFmpeg supports PCM, float WAV and other formats used by imports.
            # Spool stderr to disk so a verbose decoder failure cannot block stdout.
            with tempfile.TemporaryFile() as errors:
                with subprocess.Popen([
                    ensure_ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin",
                    "-i", str(wav_path), "-map", "0:a:0", "-ac", "1",
                    "-ar", str(ANALYSIS_RATE), "-f", "f32le", "pipe:1",
                ], stdout=subprocess.PIPE, stderr=errors) as process:
                    try:
                        candidates = detect_stream(process.stdout, ANALYSIS_RATE)
                    except BaseException:
                        process.kill()
                        raise
                    if process.wait() != 0:
                        errors.seek(0)
                        raise RuntimeError(errors.read(2000).decode(errors="replace"))
            # Publish only after successful decoding. Empty files replace stale results.
            with tempfile.TemporaryDirectory(dir=output_dir) as staging:
                csv_name = f"{wav_path.stem}_wingbeats.csv"
                label_name = f"{wav_path.stem}_audacity.txt"
                with (Path(staging) / csv_name).open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.writer(handle)
                    writer.writerow(["start_sec", "end_sec", "code", "review_required", "periodicity"])
                    for item in candidates:
                        writer.writerow([f"{item.start:.3f}", f"{item.end:.3f}", "WING", "true", f"{item.periodicity:.3f}"])
                (Path(staging) / label_name).write_text("".join(
                    f"{item.start:.3f}\t{item.end:.3f}\tWING (review required)\n" for item in candidates
                ), encoding="utf-8")
                for name in (csv_name, label_name):
                    (Path(staging) / name).replace(output_dir / name)
            return AnalyzerResult(self.name, True, output_dir, len(candidates), "Possible wingbeats; manual review required.")
        except Exception as exc:
            return AnalyzerResult(self.name, False, output_dir, message=str(exc))


register(WingbeatsPlugin())
