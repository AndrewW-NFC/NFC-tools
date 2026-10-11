"""Localized upper-band pulses need neither a bass component nor a thin whistle."""
import io

import numpy as np
import pytest

from nfc_tools.analyzers.wingbeat_accompaniment import (
    ANALYSIS_RATE,
    _pulse_lobe_widths,
    accompaniment_features,
    accompaniment_spectral_support,
    localized_pulse_support,
    screen_accompaniment,
)
from nfc_tools.analyzers.wingbeats import detect_stream


def localized_noise(seed, center=5000, width=350, *, pulsed=True):
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    noise = np.random.default_rng(seed).normal(size=len(t))
    frequency = np.fft.rfftfreq(len(t), 1 / ANALYSIS_RATE)
    band = np.fft.irfft(np.fft.rfft(noise)
                       * np.exp(-.5 * ((frequency - center) / width) ** 2), n=len(t))
    band *= .06 / np.std(band)
    envelope = .03 + np.maximum(0, np.sin(2 * np.pi * 8 * t)) ** 4 if pulsed else 1
    # Strong unrelated sound below 3 kHz hides the pulses from the broadband
    # screen; no useful bass or prominent upper-band whistle is supplied.
    return band * envelope + .15 * np.sin(2 * np.pi * 1100 * t)


@pytest.mark.parametrize('seed', range(5))
@pytest.mark.parametrize('center', [4000, 5000, 7200])
@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_recovers_localized_upper_band_noise_without_bass(seed, center, gain):
    samples = localized_noise(seed, center) * gain
    features = accompaniment_features(samples)
    assert not any(accompaniment_spectral_support(f) for f in features)
    assert any(localized_pulse_support(f) for f in features)
    assert screen_accompaniment(features) is not None


@pytest.mark.parametrize('seed', range(5))
def test_stationary_localized_noise_is_not_a_pulse_train(seed):
    samples = localized_noise(seed, pulsed=False)
    assert screen_accompaniment(accompaniment_features(samples)) is None


def test_stream_recovers_short_localized_train_at_offset():
    samples = np.r_[np.zeros(6000), localized_noise(2), np.zeros(6000)]
    hits = detect_stream(io.BytesIO(samples.astype('<f4').tobytes()), ANALYSIS_RATE)
    assert hits and any(hit.start < 2.25 and hit.end > .25 for hit in hits)


def test_width_measure_rejects_tones_plateaus_and_spectral_edges():
    frequency = np.fft.rfftfreq(1024, 1 / ANALYSIS_RATE)
    tone = np.zeros(513)
    tone[210] = 1
    assert _pulse_lobe_widths(tone, 210)[0] < 500
    assert _pulse_lobe_widths(np.ones(513), 210) == (0., 0.)
    for center in (300, 10000):
        excess = np.exp(-.5 * ((frequency - center) / 350) ** 2)
        assert _pulse_lobe_widths(excess, int(round(center / frequency[1]))) == (0., 0.)
    assert _pulse_lobe_widths(np.zeros(513), 210) == (0., 0.)


def test_lobe_widths_are_gain_invariant_and_measure_real_bandwidth():
    frequency = np.fft.rfftfreq(1024, 1 / ANALYSIS_RATE)
    excess = np.exp(-.5 * ((frequency - 5000) / 250) ** 2)
    reference = _pulse_lobe_widths(excess, 213)
    assert 500 <= reference[0] <= 3000
    assert reference[1] >= 400
    for gain in (.01, .1, 3, 100):
        np.testing.assert_allclose(_pulse_lobe_widths(excess * gain, 213), reference)
