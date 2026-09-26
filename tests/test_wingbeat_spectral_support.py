"""Noise bursts need bass support; a real wing whistle can be high-frequency."""
import numpy as np
import pytest

from nfc_tools.analyzers.wingbeat_accompaniment import (
    accompaniment_features,
    screen_accompaniment,
)
from nfc_tools.analyzers.wingbeats import screen_window, window_features


def restricted_pulses(seed, sample_rate, carrier=None):
    t = np.arange(2 * sample_rate) / sample_rate
    noise = np.random.default_rng(seed).normal(0, .04, len(t))
    spectrum = np.fft.rfft(noise)
    spectrum[np.fft.rfftfreq(len(t), 1 / sample_rate) < 900] = 0
    noise = np.fft.irfft(spectrum, n=len(t))
    pulse = .03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    tone = 0 if carrier is None else .2 * np.sin(2 * np.pi * carrier * t)
    return (noise + tone) * pulse


@pytest.mark.parametrize('seed', range(10))
@pytest.mark.parametrize('sample_rate', [8000, 24000])
def test_rejects_repeating_restricted_noise_bursts(seed, sample_rate):
    samples = restricted_pulses(seed, sample_rate)
    features = window_features(samples, sample_rate)
    assert features.periodicity >= .6  # Rhythm alone is convincing.
    assert features.low_band_fraction < .005
    assert screen_window(samples, sample_rate) is None


@pytest.mark.parametrize('seed', range(5))
@pytest.mark.parametrize('carrier', [1532.1, 2732.1, 5432.1, 7832.1])
@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_retains_high_pass_whistle_with_synchronous_noise(seed, carrier, gain):
    samples = restricted_pulses(seed, 24000, carrier) * gain
    features = accompaniment_features(samples)
    accepted = [f for f in features if screen_accompaniment([f]) is not None]
    assert accepted
    assert all(f.low_band_fraction < .005 for f in accepted)
    assert screen_window(samples, 24000) is not None


@pytest.mark.parametrize('seed', range(5))
def test_retains_broadband_wing_pulses_with_restricted_noise_background(seed):
    t = np.arange(48000) / 24000
    noise = np.random.default_rng(seed).normal(0, .08, len(t))
    wing = noise * (.03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4)
    background = restricted_pulses(seed + 10, 24000) * .3
    assert screen_window(wing + background, 24000) is not None
