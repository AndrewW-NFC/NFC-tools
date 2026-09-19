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
WINDOW_SECONDS = 4
HOP_SECONDS = 2


@dataclass(frozen=True)
class Candidate:
    start: float
    end: float
    periodicity: float  # Similarity of repeated pulses, NOT a probability.


def screen_window(samples: np.ndarray) -> float | None:
    """Screen 1–4 seconds for broadband pulses repeating approximately 2–20 Hz.

    All cutoffs are provisional engineering choices requiring field validation.
    Spectral flatness rejects tones; modulation and autocorrelation reject steady
    noise and isolated transients. Rhythmic machinery/rain can still pass.
    """
    if len(samples) < SAMPLE_RATE or not np.isfinite(samples).all():
        return None
    frames = np.lib.stride_tricks.sliding_window_view(samples, 256)[::80]
    power = np.abs(np.fft.rfft(frames * np.hanning(256), axis=1)) ** 2
    frequencies = np.fft.rfftfreq(256, 1 / SAMPLE_RATE)
    band = power[:, (frequencies >= 150) & (frequencies <= 3000)]
    envelope = np.sqrt(band.sum(axis=1))
    if envelope.max() < 1e-4:
        return None
    spectrum = band.mean(axis=0) + 1e-20
    flatness = np.exp(np.log(spectrum).mean()) / spectrum.mean()
    if flatness < 0.12:
        return None
    low, high = np.percentile(envelope, [10, 90])
    if (high - low) / (high + 1e-20) < 0.45:
        return None
    centered = envelope - envelope.mean()
    correlations = []
    for lag in range(5, min(51, len(envelope) // 4)):
        left, right = centered[:-lag], centered[lag:]
        denom = np.linalg.norm(left) * np.linalg.norm(right)
        correlations.append(float(np.dot(left, right) / denom) if denom else 0.0)
    score = max(correlations, default=0.0)
    if score < 0.6:
        return None
    # Require multiple distinct pulses, rather than one loud rustle.
    above = envelope > low + 0.6 * (high - low)
    rises = np.count_nonzero(above[1:] & ~above[:-1]) + int(above[0])
    return score if rises >= 4 else None


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
