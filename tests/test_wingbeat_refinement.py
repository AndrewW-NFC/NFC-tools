import io

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeats
from nfc_tools.analyzers.wingbeat_accompaniment import (
    accompaniment_features,
    screen_accompaniment,
)


def jittered_whistle(*, synchronous=True):
    rng = np.random.default_rng(4)
    t = np.arange(48000) / 24000
    centers = np.arange(.1, 1.95, 1 / 7) + rng.normal(0, .018, 13)
    envelope = .03 + sum(np.exp(-((t - c) / .018) ** 2) for c in centers)
    noise = rng.normal(0, .04, len(t))
    return (.2 * np.sin(2 * np.pi * 5432.1 * t) * envelope
            + noise * (envelope if synchronous else 1))


def test_near_miss_recovers_jittered_whistle_only_with_synchronous_noise():
    features = accompaniment_features(jittered_whistle())
    assert screen_accompaniment(features) is None
    score = screen_accompaniment(features, allow_near_miss=True)
    assert .55 <= score < .60  # Keep the measured score; do not inflate it.
    assert screen_accompaniment(
        accompaniment_features(jittered_whistle(synchronous=False)), allow_near_miss=True,
    ) is None


def test_shorter_pass_does_not_relax_the_rhythm_gates():
    samples = jittered_whistle()
    assert wingbeats.screen_window(samples, 24000) is None
    assert wingbeats.screen_window(samples, 24000, pass_kind='long') is not None
    assert wingbeats.screen_window(samples, 24000, pass_kind='accompaniment') is not None


def test_short_window_detection_and_nested_interval_merge(monkeypatch):
    # Ramp values identify absolute positions regardless of decoder read size.
    samples = np.arange(4 * 24000, dtype='<f4')

    def screen(chunk, rate, *, pass_kind):
        start = chunk[0] / rate
        if start == 1 and len(chunk) == 2 * rate:
            return .8
        if start == 1 and len(chunk) == int(1.5 * rate):
            return .9
        if start == 1.75 and len(chunk) == int(1.5 * rate):
            assert pass_kind == 'standard'
            return .7
        return None

    monkeypatch.setattr(wingbeats, 'screen_window', screen)
    result = wingbeats.detect_stream(io.BytesIO(samples.tobytes()), 24000)
    assert result == [wingbeats.Candidate(1, 3.25, .9)]


@pytest.mark.parametrize('tail_samples', [0, 1, 12000, 18000, 23999])
def test_stream_short_reads_and_tails_match_contiguous_reads(tail_samples):
    class ShortReads(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(size, 997))

    samples = np.r_[jittered_whistle(), np.zeros(tail_samples)].astype('<f4')
    raw = samples.tobytes()
    expected = wingbeats.detect_stream(io.BytesIO(raw), 24000)
    assert expected
    assert wingbeats.detect_stream(ShortReads(raw), 24000) == expected
    assert all(hit.end <= len(samples) / 24000 for hit in expected)


def test_refined_stream_rejects_truncated_pcm():
    with pytest.raises(ValueError, match='Truncated'):
        wingbeats.detect_stream(io.BytesIO(b'bad'), 24000)
