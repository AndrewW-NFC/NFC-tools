"""Brief accompaniment windows retain strict gates and streaming boundaries."""
import io

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeats as w
from test_wingbeat_accompaniment import whistle
from test_wingbeat_refinement import jittered_whistle


@pytest.mark.parametrize('seed', range(3))
def test_brief_pass_finds_train_obscured_by_surrounding_noise(seed):
    samples = np.random.default_rng(seed).normal(0, .1, 48000)
    samples[6000:30000] = whistle(seed)[:24000]
    assert w.screen_window(samples, 24000, pass_kind='long') is None
    assert w.screen_window(samples[:36000], 24000) is None
    assert w.screen_window(samples[6000:30000], 24000, pass_kind='brief') is not None


def test_brief_pass_cannot_use_near_miss_rhythm_or_legacy_rate():
    samples = jittered_whistle()
    assert w.screen_window(samples, 24000, pass_kind='accompaniment') is not None
    assert w.screen_window(samples, 24000, pass_kind='brief') is None
    assert w.screen_window(samples, 8000, pass_kind='brief') is None


@pytest.mark.parametrize('kind', ['tone', 'stationary', 'harmonics', 'sweep'])
@pytest.mark.parametrize('frequency', [1532.1, 2732.1, 5432.1, 7832.1])
def test_brief_windows_reject_tones_and_unrelated_noise(kind, frequency):
    samples = whistle(frequency=frequency, kind=kind)
    for offset in range(0, 24001, 6000):
        assert w.screen_window(samples[offset:offset + 24000], 24000, pass_kind='brief') is None


@pytest.mark.parametrize('size', [23999, 24000, 30001, 48000, 96001])
def test_brief_schedule_uses_complete_windows_without_padding(size):
    samples = np.arange(size, dtype='<f4')
    windows = list(w.analysis_windows(io.BytesIO(samples.tobytes()), 24000))
    brief = [(start, x) for start, x, kind in windows if kind == 'brief']
    assert [start for start, _ in brief] == [offset / 24000 for offset in range(0, size - 24000 + 1, 6000)]
    for start, x in brief:
        np.testing.assert_array_equal(x, samples[round(start * 24000):round(start * 24000) + 24000])
    assert all(kind != 'brief' for _, _, kind in w.analysis_windows(io.BytesIO(samples.tobytes()), 8000))


def test_brief_only_hit_merges_with_an_overlapping_long_hit(monkeypatch):
    def screen(samples, rate, *, pass_kind):
        start = samples[0] / rate
        if pass_kind == 'brief' and start == .25:
            return .95
        if pass_kind == 'long' and start == 1:
            return .7
        return None

    monkeypatch.setattr(w, 'screen_window', screen)
    samples = np.arange(4 * 24000, dtype='<f4')
    assert w.detect_stream(io.BytesIO(samples.tobytes()), 24000) == [w.Candidate(.25, 3., .95)]
