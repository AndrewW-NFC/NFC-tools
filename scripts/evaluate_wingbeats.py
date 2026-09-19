"""Offline diagnostic sweep; synthetic results do not estimate field accuracy.

Usage: python scripts/evaluate_wingbeats.py /path/to/known-wingbeats.wav
"""
import argparse
import io
import subprocess

import numpy as np

from nfc_tools.analyzers.wingbeats import SAMPLE_RATE, detect_stream
from nfc_tools.ffmpeg_locator import ensure_ffmpeg

KINDS = (
    "white", "pink", "wind", "clicks", "swell", "tone", "chirps",
    "tonal_calls", "pulse_train", "low_contrast", "jittered",
)


def synthetic_signal(kind: str, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(4 * SAMPLE_RATE) / SAMPLE_RATE
    noise = rng.normal(0, 0.1, len(t))
    pulses = np.maximum(0, np.sin(2 * np.pi * 7 * t))
    chirp = np.sin(2 * np.pi * (1500 * t + 1000 * t * t))
    if kind in {"pink", "wind"}:
        frequency = np.fft.rfftfreq(len(t), 1 / SAMPLE_RATE)
        slope = 0.5 if kind == "pink" else 1
        signal = np.fft.irfft(
            np.fft.rfft(noise) / np.maximum(frequency, 1) ** slope, n=len(t),
        )
        return signal / np.std(signal) * 0.1
    if kind == "clicks":
        signal = noise.copy()
        for location in rng.integers(0, len(t) - 100, 20):
            signal[location:location + 100] += rng.normal(0, 1, 100)
        return signal
    if kind == "swell":
        return noise * (0.1 + np.exp(-((t - 2) / 0.3) ** 2))
    if kind == "tone":
        return 0.2 * np.sin(2 * np.pi * 1000 * t) * (0.1 + pulses)
    if kind == "chirps":
        return 0.2 * chirp * (0.1 + pulses)
    if kind == "tonal_calls":
        return noise * 0.02 + 0.2 * chirp * pulses ** 4
    if kind == "pulse_train":
        return noise * (0.02 + pulses ** 4)
    if kind == "low_contrast":
        return noise * (1 + 0.25 * np.sin(2 * np.pi * 7 * t))
    if kind == "jittered":
        phase = 2 * np.pi * (7 * t + 0.08 * np.sin(2 * np.pi * 1.1 * t))
        return noise * (0.02 + np.maximum(0, np.sin(phase)) ** 4)
    return noise


def detect(samples):
    return detect_stream(io.BytesIO(samples.astype("<f4").tobytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", help="Known-positive recording; never modified")
    args = parser.parse_args()
    raw = subprocess.check_output([
        ensure_ffmpeg(), "-v", "error", "-i", args.recording,
        "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-",
    ])
    samples = np.frombuffer(raw, dtype="<f4")
    print("Sample gain and alignment checks (gain, padding seconds, intervals):")
    for gain in (0.1, 1, 3):
        for padding in (0, 0.25, 0.5, 0.75):
            signal = np.concatenate([np.zeros(int(padding * SAMPLE_RATE)), samples * gain])
            print(gain, padding, [(d.start, d.end) for d in detect(signal)])
    print("Synthetic examples with at least one candidate:")
    for kind in KINDS:
        hits = sum(bool(detect(synthetic_signal(kind, seed))) for seed in range(100))
        print(f"{kind}: {hits}/100")


if __name__ == "__main__":
    main()
