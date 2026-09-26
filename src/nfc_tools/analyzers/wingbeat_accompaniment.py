"""Experimental pulse-linked energy around spectral ridges; not a species ID."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ANALYSIS_RATE = 24000
SEARCH_BANDS = ((700, 2200), (1800, 4000), (3500, 6500), (6000, 9500))
MIN_LOW_BAND_FRACTION = .005
MIN_RIDGE_PROMINENCE = 16.0


@dataclass(frozen=True)
class AccompanimentFeatures:
    lower_hz: int
    upper_hz: int
    periodicity: float
    repeat_periodicity: float
    modulation: float
    noise_coherence: float
    noise_contrast: float
    noise_ratio: float
    ridge_share: float
    residual_bins: float
    pulse_count: int
    peak_envelope: float
    noise_center_hz: float
    low_band_fraction: float
    ridge_prominence: float


def low_band_fractions(power: np.ndarray, frequency: np.ndarray) -> np.ndarray:
    """150–600 Hz energy relative to 150–3000 Hz, independently per frame."""
    low = power[:, (frequency >= 150) & (frequency < 600)].sum(axis=1)
    total = power[:, (frequency >= 150) & (frequency <= 3000)].sum(axis=1)
    return low / (total + 1e-20)


def _smooth(values: np.ndarray, size: int) -> np.ndarray:
    return np.convolve(np.pad(values, size // 2, mode="symmetric"), np.ones(size) / size, mode="valid")


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    left, right = left - left.mean(), right - right.mean()
    denominator = np.linalg.norm(left) * np.linalg.norm(right)
    return float(np.dot(left, right) / denominator) if denominator else 0.0


def distinct_pulses(envelope: np.ndarray, threshold: float, period: int) -> int:
    """Count separated pulse peaks, not multiple crossings within one event."""
    # First collapse each continuous above-threshold region to one peak.
    # Counting all local maxima would turn a single noisy swell into a train.
    above = np.r_[False, envelope > threshold, False]
    starts = np.flatnonzero(above[1:] & ~above[:-1])
    ends = np.flatnonzero(~above[1:] & above[:-1])
    candidates = np.array([
        start + int(np.argmax(envelope[start:end]))
        for start, end in zip(starts, ends)
    ], dtype=int)
    selected = []
    for peak in candidates[np.argsort(envelope[candidates])[::-1]]:
        if all(abs(int(peak) - other) >= .6 * period for other in selected):
            selected.append(int(peak))
    return len(selected)


def accompaniment_features(samples: np.ndarray) -> list[AccompanimentFeatures]:
    """Measure 24 kHz mono PCM; exclude strong ridges, harmonics and guard bins.

    A spectral maximum is searched independently in four overlapping bands.
    Residual energy is measured 211–1055 Hz either side of the window-median
    ridge location. These frequency regions stay fixed through pulses and gaps,
    excluding all peaks >8x their local spectral median plus six guard bins.
    This is a leakage precaution, not proof that the residual is aerodynamic.
    """
    if len(samples) < ANALYSIS_RATE or not np.isfinite(samples).all():
        return []
    frames = np.lib.stride_tricks.sliding_window_view(samples, 1024)[::240]
    power = np.abs(np.fft.rfft(frames * np.hanning(1024), axis=1)) ** 2
    frequency = np.fft.rfftfreq(1024, 1 / ANALYSIS_RATE)
    spectral_neighborhoods = np.lib.stride_tricks.sliding_window_view(
        np.pad(power, ((0, 0), (10, 10)), mode="edge"), 21, axis=1,
    )
    local_median = np.median(spectral_neighborhoods, axis=-1)
    peaks = (power > 8 * local_median) & (power > power.max(axis=1, keepdims=True) * .001)
    masked = np.lib.stride_tricks.sliding_window_view(
        np.pad(peaks, ((0, 0), (6, 6)), mode="edge"), 13, axis=1,
    ).any(axis=-1)
    bins = np.arange(power.shape[1])[None, :]
    low_fraction = low_band_fractions(power, frequency)
    results = []
    for lower, upper in SEARCH_BANDS:
        in_band = (frequency >= lower) & (frequency < upper)
        ridge = np.argmax(power[:, in_band], axis=1) + np.flatnonzero(in_band)[0]
        distance = np.abs(bins - ridge[:, None])
        tone = _smooth(np.sqrt((power * (distance <= 2)).sum(axis=1)), 3)
        # A fading whistle can hand the per-frame maximum to background noise.
        # Moving the residual region with it compares different spectra during
        # pulses and gaps, creating apparent modulation in stationary noise.
        # Hold the region fixed for this window while retaining per-frame masks
        # to exclude strong tones/harmonics as their frequencies change.
        noise_center = int(np.median(ridge))
        residual_distance = np.abs(bins - noise_center)
        residual = ((residual_distance >= 9) & (residual_distance <= 45) & ~masked
                    & (frequency[None, :] >= 300) & (frequency[None, :] <= 10000))
        above = residual & (bins > noise_center)
        below = residual & ~above
        lower_power = (power * below).sum(axis=1) / np.maximum(1, below.sum(axis=1))
        upper_power = (power * above).sum(axis=1) / np.maximum(1, above.sum(axis=1))
        noise = _smooth(np.sqrt((lower_power + upper_power) / 2), 3)
        # Remove slower loudness changes before testing pulse synchrony.
        centered = tone - _smooth(tone, 51)
        noise_centered = noise - _smooth(noise, 51)
        correlations = [0.0] + [
            _correlation(centered[:-lag], centered[lag:])
            for lag in range(1, min(101, len(centered) // 2))
        ]
        lags = [lag for lag in range(5, min(51, len(centered) // 4))
                if correlations[lag] > correlations[lag - 1]
                and correlations[lag] >= correlations[lag + 1]]
        best = max(lags, key=lambda lag: correlations[lag], default=None)
        if best is None:
            continue
        on = centered >= np.percentile(centered, 75)
        off = centered <= np.percentile(centered, 25)
        contrast = (noise[on].mean() - noise[off].mean()) / (noise[on].mean() + 1e-20)
        low, high = np.percentile(tone, [10, 90])
        count = distinct_pulses(tone, low + .6 * (high - low), best)
        results.append(AccompanimentFeatures(
            lower, upper, correlations[best],
            _correlation(centered[:-2 * best], centered[2 * best:]),
            float((high - low) / (high + 1e-20)),
            _correlation(centered, noise_centered), float(contrast),
            float(np.median(noise) / (np.median(tone) + 1e-20)),
            float(np.median(power[np.arange(len(power)), ridge][on]
                            / (power.max(axis=1)[on] + 1e-20))),
            float(np.median(residual.sum(axis=1))), count, float(tone.max()),
            float(frequency[noise_center]),
            float(np.median(low_fraction[on])),
            float(np.median((power[np.arange(len(power)), ridge]
                             / (local_median[np.arange(len(power)), ridge] + 1e-20))[on])),
        ))
    return results


def accompaniment_rhythm_passes(item: AccompanimentFeatures, *, allow_near_miss: bool = False) -> bool:
    """A weaker first repeat needs stronger second-repeat and synchrony evidence."""
    return (item.periodicity >= .60 and item.repeat_periodicity >= .35) or (
        allow_near_miss and item.periodicity >= .55
        and item.repeat_periodicity >= .40 and item.noise_coherence >= .70
    )


def screen_accompaniment(
    features: list[AccompanimentFeatures], *, allow_near_miss: bool = False,
) -> float | None:
    """Require low-band support or a prominent ridge for restricted spectra.

    High-pass noise bursts have maxima too; synchrony with their neighboring
    noise alone is insufficient evidence of a tonal wing sound. A ridge at
    least 16x its local median preserves the tonal route without bass support.
    These are provisional cutoffs, not a general rain/insect classifier.
    """
    scores = [item.periodicity for item in features
              if item.peak_envelope >= 1e-4 and item.pulse_count >= 4
              and accompaniment_rhythm_passes(item, allow_near_miss=allow_near_miss)
              and item.modulation >= .25 and item.noise_coherence >= .40
              and item.noise_contrast >= .15 and item.noise_ratio >= .005 and item.ridge_share >= .001
              and item.residual_bins >= 20
              and (item.low_band_fraction >= MIN_LOW_BAND_FRACTION
                   or item.ridge_prominence >= MIN_RIDGE_PROMINENCE)]
    return max(scores, default=None)
