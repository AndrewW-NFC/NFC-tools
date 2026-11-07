"""Swept-call rejection must preserve stable/no-bass and overlapping wing pulses."""

# Role: Run by pytest to protect the behavior exercised by the tests below.
# Dependencies: pytest runs the tests. Project/external imports:
# nfc_tools.analyzers.wingbeat_accompaniment, nfc_tools.analyzers.wingbeats, numpy,
# pytest, test_wingbeat_research.
from dataclasses import replace
import io
import json
from pathlib import Path

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream


def swept_noise():
    t = np.arange(48000) / a.ANALYSIS_RATE
    noise = np.random.default_rng(4).normal(size=len(t))
    hz = np.fft.rfftfreq(len(t), 1 / a.ANALYSIS_RATE)
    noise = np.fft.irfft(np.fft.rfft(noise) * np.exp(-.5 * (hz / 200) ** 2), n=len(t))
    noise *= .1 / np.std(noise)
    frequency = 5000 + 1000 * np.sin(2 * np.pi * 2 * t)
    signal = noise * np.cos(2 * np.pi * np.cumsum(frequency) / a.ANALYSIS_RATE)
    return (signal * (.03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 2)
            + .15 * np.sin(2 * np.pi * 1100 * t))


@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_sweeping_noise_previously_passed_but_now_is_rejected(gain):
    samples = swept_noise() * gain
    features = a.accompaniment_features(samples)
    baseline = [replace(f, pulse_centroid_range_hz=0, pulse_width_ratio=1) for f in features]
    assert a.screen_accompaniment(baseline) is not None
    assert any(a.swept_call_interference(f) for f in features)
    assert a.screen_accompaniment(features) is None


def test_motion_features_are_gain_invariant_and_cache_independent():
    samples = swept_noise()
    expected = a.accompaniment_features(samples)
    for gain in (.1, 3):
        actual = a.accompaniment_features(samples * gain)
        np.testing.assert_allclose(
            [(f.pulse_centroid_range_hz, f.pulse_width_ratio) for f in actual],
            [(f.pulse_centroid_range_hz, f.pulse_width_ratio) for f in expected], rtol=1e-10,
        )
    raw = samples.astype('<f4').tobytes()
    assert detect_stream(io.BytesIO(raw), a.ANALYSIS_RATE) == detect_stream(
        io.BytesIO(raw), a.ANALYSIS_RATE, reuse_frames=False)


def test_broad_wings_remain_detectable_over_sweeping_calls():
    samples = swept_noise()
    t = np.arange(len(samples)) / a.ANALYSIS_RATE
    wings = np.random.default_rng(9).normal(0, .12, len(t))
    wings *= .03 + np.maximum(0, np.sin(2 * np.pi * 8 * t)) ** 4
    assert detect_stream(io.BytesIO((samples + wings).astype('<f4').tobytes()), a.ANALYSIS_RATE)


def test_silent_motion_has_no_rejection_evidence():
    assert a._pulse_frequency_motion(a._motion_power(np.zeros(24000)), 4500) == (0., 1.)


ROWS = json.loads((Path(__file__).parent / 'fixtures/robin-motion-features.json').read_text())


@pytest.mark.parametrize('row', ROWS, ids=lambda row: row['id'])
def test_measured_robin_and_field_windows(row):
    feature = a.AccompanimentFeatures(**row['features'])
    assert a.screen_accompaniment([
        replace(feature, pulse_centroid_range_hz=0, pulse_width_ratio=1)
    ], allow_near_miss=True) is not None
    assert (a.screen_accompaniment([feature], allow_near_miss=True) is None) == row['reject']


def test_research_reports_motion_rejection():
    from test_wingbeat_research import scan

    row = scan.instrument_window(swept_noise().astype('<f4'), 0.)
    assert not row['current_detect']
    assert row['acc_3500_6500_pulse_centroid_range_hz'] >= 700
    assert 'swept_call_interference' in row['acc_3500_6500_failed_gates']
