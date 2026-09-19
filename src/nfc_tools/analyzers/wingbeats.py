"""Experimental pulse-train screening; WING means possible wingbeats, not an ID."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from .base import AnalyzerResult, register
from ..ffmpeg_locator import ensure_ffmpeg

SAMPLE_RATE = 8000
WINDOW_SECONDS = 2
HOP_SECONDS = 1


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


def window_features(samples: np.ndarray) -> WindowFeatures | None:
    """Measure a window for diagnostics and screening; scores are not probabilities."""
    if len(samples) < SAMPLE_RATE or not np.isfinite(samples).all():
        return None
    frames = np.lib.stride_tricks.sliding_window_view(samples, 256)[::80]
    power = np.abs(np.fft.rfft(frames * np.hanning(256), axis=1)) ** 2
    frequencies = np.fft.rfftfreq(256, 1 / SAMPLE_RATE)
    band = power[:, (frequencies >= 150) & (frequencies <= 3000)]
    # Assess individual frames: averaging spectra first makes a sweeping tone
    # look broadband, even though it is narrowband at every instant.
    frame_flatness = np.exp(np.log(band + 1e-20).mean(axis=1)) / (band.mean(axis=1) + 1e-20)
    envelope = np.sqrt(band.sum(axis=1))
    # 30 ms smoothing reduces frame-to-frame noise without erasing the pulses.
    envelope = np.convolve(envelope, np.ones(3) / 3, mode="valid")
    loud = envelope >= np.percentile(envelope, 75)
    flatness = float(np.median(frame_flatness[1:-1][loud]))
    low, high = np.percentile(envelope, [10, 90])
    modulation = float((high - low) / (high + 1e-20))
    centered = envelope - envelope.mean()
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
    above = envelope > low + 0.6 * (high - low)
    pulses = int(np.count_nonzero(above[1:] & ~above[:-1]) + int(above[0]))
    return WindowFeatures(
        flatness, modulation, correlations[best] if best else 0.0,
        correlations[2 * best] if best else 0.0, pulses, float(envelope.max()),
    )


def screen_window(samples: np.ndarray) -> float | None:
    """Screen for repeated broadband pulses at approximately 2–20 Hz.

    Provisional engineering cutoffs: not a trained or calibrated classifier.
    Background sound can reduce modulation, so accept moderate contrast only
    when the envelope repeats at both one and two pulse periods.
    """
    features = window_features(samples)
    if features is None:
        return None
    if (features.peak_envelope < 1e-4 or features.spectral_flatness < 0.12
            or features.modulation < 0.25 or features.periodicity < 0.6
            or features.repeat_periodicity < 0.35 or features.pulse_count < 4):
        return None
    return features.periodicity


def detect_stream(stream) -> list[Candidate]:
    """Read mono float32 PCM in overlapping windows, bounded audio memory."""
    window_bytes = SAMPLE_RATE * WINDOW_SECONDS * 4
    hop_bytes = SAMPLE_RATE * HOP_SECONDS * 4
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
        score = screen_window(samples)
        if score is not None:
            end = offset + len(samples) / SAMPLE_RATE
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
                    "-ar", str(SAMPLE_RATE), "-f", "f32le", "pipe:1",
                ], stdout=subprocess.PIPE, stderr=errors) as process:
                    try:
                        candidates = detect_stream(process.stdout)
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
