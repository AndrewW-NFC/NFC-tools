"""Caching must preserve every window's features and merged detections."""
import io

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeats as w
from nfc_tools.analyzers.wingbeat_accompaniment import accompaniment_features, accompaniment_frames
from nfc_tools.analyzers.wingbeat_frames import FrameCache


def signal(kind, seconds=3.37, rate=24000):
    t = np.arange(int(seconds * rate)) / rate
    noise = np.random.default_rng(53).normal(0, .04, len(t))
    pulses = .03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    if kind == 'pulses':
        noise *= pulses
    elif kind == 'ridge':
        noise = (noise + .2 * np.sin(2 * np.pi * 5432.1 * t)) * pulses
    elif kind == 'silence':
        noise[:] = 0
    return noise.astype('<f4')


@pytest.mark.parametrize('kind', ['noise', 'pulses', 'ridge', 'silence'])
def test_every_window_feature_and_candidate_is_unchanged(kind):
    samples = signal(kind)
    broadband = FrameCache(768, 240, w.broadband_frames)
    accompaniment = FrameCache(1024, 240, accompaniment_frames)
    for offset, chunk, _ in w.analysis_windows(io.BytesIO(samples.tobytes()), 24000):
        start = round(offset * 24000)
        assert w.window_features(chunk, 24000, frame_cache=broadband, offset=start) == w.window_features(chunk, 24000)
        assert accompaniment_features(chunk, frame_cache=accompaniment, offset=start) == accompaniment_features(chunk)
        assert len(broadband.arrays[0]) <= 197
        assert len(accompaniment.arrays[0]) <= 196
    assert w.detect_stream(io.BytesIO(samples.tobytes()), 24000) == w.detect_stream(
        io.BytesIO(samples.tobytes()), 24000, reuse_frames=False,
    )


@pytest.mark.parametrize('rate', [8000, 24000])
def test_cache_preserves_short_reads_nonfinite_audio_and_tail(rate):
    class ShortReads(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(size, 997))

    samples = signal('pulses', seconds=4.13, rate=rate)
    samples[rate] = np.nan
    expected = w.detect_stream(io.BytesIO(samples.tobytes()), rate, reuse_frames=False)
    assert w.detect_stream(ShortReads(samples.tobytes()), rate) == expected


def test_overlap_computed_once_and_cache_stays_bounded():
    computed = 0

    def transform(frames):
        nonlocal computed
        computed += len(frames)
        return (frames.copy(),)

    samples = np.arange(10000)
    cache = FrameCache(32, 10, transform)
    for offset in range(0, 9000, 50):
        for length in (100, 200, 150):
            actual, = cache.get(samples[offset:offset + length], offset)
            expected = np.lib.stride_tricks.sliding_window_view(samples[offset:offset + length], 32)[::10]
            np.testing.assert_array_equal(actual, expected)
            assert len(cache.arrays[0]) <= 17
    assert computed == (8950 + 200 - 32) // 10 + 1
