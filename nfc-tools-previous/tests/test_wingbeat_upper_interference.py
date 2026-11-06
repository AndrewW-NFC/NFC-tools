"""Reject an insect-like companion lobe without a general high-frequency veto."""
import io
from dataclasses import replace

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream


def paired_pulses(seed, *, lower_pulses=False, upper_rate=8):
    t = np.arange(2 * a.ANALYSIS_RATE) / a.ANALYSIS_RATE
    frequency = np.fft.rfftfreq(len(t), 1 / a.ANALYSIS_RATE)
    rng = np.random.default_rng(seed)

    def noise_band(center, width):
        noise = rng.normal(size=len(t))
        shaped = np.fft.irfft(np.fft.rfft(noise)
                             * np.exp(-.5 * ((frequency - center) / width) ** 2), n=len(t))
        return shaped / np.std(shaped)

    pulse = np.maximum(0, np.sin(2 * np.pi * 8 * t)) ** 4
    upper = np.maximum(0, np.sin(2 * np.pi * upper_rate * t)) ** 4
    samples = (.02 * noise_band(6800, 350) * (.15 + pulse)
               + .08 * noise_band(8500, 250) * (.003 + upper)
               + .15 * np.sin(2 * np.pi * 1100 * t)
               + .03 * noise_band(5000, 350))
    if lower_pulses:
        samples += .04 * noise_band(5000, 350) * (.01 + pulse)
    return samples


@pytest.mark.parametrize('seed', range(5))
@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_rejects_dominant_upper_pulses_with_a_weaker_companion_lobe(seed, gain):
    features = a.accompaniment_features(paired_pulses(seed) * gain)
    # This is a regression against a previously accepted signal, not just a
    # negative that unrelated pre-existing checks would already reject.
    previous = [replace(f, upper_pulse_dominance=0.) for f in features]
    assert a.screen_accompaniment(previous) is not None
    assert a.screen_accompaniment(features) is None


@pytest.mark.parametrize('seed', range(5))
def test_synchronized_lower_pulses_preserve_localized_support(seed):
    features = a.accompaniment_features(paired_pulses(seed, lower_pulses=True))
    assert a.screen_accompaniment(features) is not None


@pytest.mark.parametrize('seed', range(5))
def test_different_upper_rhythm_does_not_veto_independent_support(seed):
    features = a.accompaniment_features(paired_pulses(seed, upper_rate=11))
    previous = [replace(f, upper_pulse_dominance=0.) for f in features]
    # Seed 3 already fails the old screen; the other four retain acceptance.
    assert a.screen_accompaniment(features) == a.screen_accompaniment(previous)


def test_existing_spectral_route_is_not_vetoed():
    features = a.accompaniment_features(paired_pulses(0))
    feature = next(f for f in features if a.upper_pulse_interference(f)
                   and a.localized_pulse_support(replace(f, upper_pulse_dominance=0.)))
    supported_whistle = replace(feature, ridge_prominence=20., pulse_excess_flatness=.4)
    assert a.upper_pulse_interference(supported_whistle)
    assert a.accompaniment_spectral_support(supported_whistle)
    assert a.screen_accompaniment([supported_whistle]) is not None


def test_stream_checks_short_windows_and_offsets():
    samples = np.r_[np.zeros(6000), paired_pulses(0), np.zeros(6000)]
    assert not detect_stream(io.BytesIO(samples.astype('<f4').tobytes()), a.ANALYSIS_RATE)


@pytest.mark.parametrize('seed', range(5))
def test_dominant_high_frequency_wing_lobe_is_preserved(seed):
    from test_wingbeat_localized_pulses import localized_noise

    features = a.accompaniment_features(localized_noise(seed, center=8500))
    assert a.screen_accompaniment(features) is not None


def test_overlapping_broadband_wing_pulses_remain_detectable():
    samples = paired_pulses(0)
    t = np.arange(len(samples)) / a.ANALYSIS_RATE
    pulse = np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    samples += .2 * np.random.default_rng(7).normal(size=len(t)) * (.01 + pulse)
    assert detect_stream(io.BytesIO(samples.astype('<f4').tobytes()), a.ANALYSIS_RATE)


def test_research_exports_interference_diagnostics():
    from test_wingbeat_research import scan

    row = scan.instrument_window(paired_pulses(0).astype('<f4'), 0.)
    assert not row['current_detect']
    assert row['acc_6000_9500_upper_pulse_dominance'] >= 3.
    assert 'upper_pulse_interference' in row['acc_6000_9500_failed_gates']
