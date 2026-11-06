"""Call-like controls for pulse-linked spectral support; no species classifier."""
import io

import numpy as np
import pytest

from nfc_tools.analyzers.wingbeat_accompaniment import (
    ANALYSIS_RATE,
    accompaniment_features,
    accompaniment_rhythm_passes,
    screen_accompaniment,
)
from nfc_tools.analyzers.wingbeats import detect_stream


def detect(samples):
    return detect_stream(io.BytesIO(samples.astype('<f4').tobytes()), ANALYSIS_RATE)


def patchy_call(seed):
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    pulse = .03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    noise = np.random.default_rng(seed).normal(size=len(t))
    frequency = np.fft.rfftfreq(len(t), 1 / ANALYSIS_RATE)
    patch = np.fft.irfft(np.fft.rfft(noise)
                        * np.exp(-.5 * ((frequency - 3900) / 120) ** 2), n=len(t))
    patch /= np.std(patch)
    return (.2 * np.sin(2 * np.pi * 3200 * t) + .05 * patch) * pulse + .003 * noise


@pytest.mark.parametrize('seed', range(5))
@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_rejects_patchy_call_residual_despite_synchronous_energy(seed, gain):
    samples = patchy_call(seed) * gain
    features = accompaniment_features(samples)
    call = next(f for f in features if f.lower_hz == 1800)
    assert accompaniment_rhythm_passes(call)
    assert call.noise_coherence >= .4 and call.noise_contrast >= .15
    assert call.pulse_excess_flatness < .03
    assert screen_accompaniment(features, allow_near_miss=True) is None
    assert not detect(samples)


@pytest.mark.parametrize('width', [.003, .006])
@pytest.mark.parametrize('gain', [.1, 1, 3])
@pytest.mark.parametrize('seed', range(3))
def test_unrelated_bass_does_not_support_weak_swept_calls(width, gain, seed):
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    phase_time = t % (1 / 7) - .07
    calls = (np.sin(2 * np.pi * (6500 * phase_time + 250000 * phase_time ** 2))
             * np.exp(-(phase_time / width) ** 2))
    samples = gain * (.3 * np.sin(2 * np.pi * 200 * t) + .2 * calls
                      + .0001 * np.random.default_rng(seed).normal(size=len(t)))
    features = accompaniment_features(samples)
    call = next(f for f in features if f.lower_hz == 6000)
    assert accompaniment_rhythm_passes(call)
    assert call.low_band_fraction > .9
    assert call.pulse_excess_flatness > .3
    assert .001 <= call.ridge_share < .01
    assert call.ridge_prominence < 5
    assert screen_accompaniment(features, allow_near_miss=True) is None
    assert not detect(samples)


def test_pulse_excess_texture_is_gain_invariant():
    reference = accompaniment_features(patchy_call(0))
    for gain in (.1, 3):
        features = accompaniment_features(patchy_call(0) * gain)
        np.testing.assert_allclose(
            [f.pulse_excess_flatness for f in features],
            [f.pulse_excess_flatness for f in reference], rtol=1e-10, atol=1e-12,
        )


@pytest.mark.parametrize('seed', range(3))
def test_retains_broad_wing_pulses_overlapping_call_like_tones(seed):
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    pulse = .03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    wings = np.random.default_rng(seed + 10).normal(0, .08, len(t)) * pulse
    assert detect(patchy_call(seed) + wings)
