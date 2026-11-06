"""A stronger neighboring sound must not hide a supported mid-band passage."""
import io
import wave
from pathlib import Path

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream


def recording(name):
    with wave.open(str(Path(__file__).parent / 'fixtures' / f'{name}.wav')) as audio:
        assert audio.getframerate() == a.ANALYSIS_RATE
        return np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2') / 32767


@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_swan_passage_needs_interior_tracker_not_looser_gates(gain):
    samples = recording('mute-swan-wings')[:36000] * gain
    features = a.accompaniment_features(samples)
    original = [f for f in features if (f.lower_hz, f.upper_hz) != (2200, 3500)]
    interior = [f for f in features if (f.lower_hz, f.upper_hz) == (2200, 3500)]
    assert a.screen_accompaniment(original, allow_near_miss=True) is None
    assert a.screen_accompaniment(interior) is not None
    assert 2500 <= interior[0].noise_center_hz <= 3000


@pytest.mark.parametrize('offset', [0, .07, .19])
@pytest.mark.parametrize('reuse_frames', [False, True])
def test_stream_recovers_swan_with_different_window_alignment(offset, reuse_frames):
    samples = np.r_[np.zeros(round(offset * a.ANALYSIS_RATE)), recording('mute-swan-wings')]
    hits = detect_stream(io.BytesIO(samples.astype('<f4').tobytes()), a.ANALYSIS_RATE,
                         reuse_frames=reuse_frames)
    assert hits and any(hit.end > offset and hit.start < offset + 2.5 for hit in hits)


@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_repeating_background_in_same_recording_is_not_recovered(gain):
    samples = recording('mute-swan-background') * gain
    assert not detect_stream(io.BytesIO(samples.astype('<f4').tobytes()), a.ANALYSIS_RATE)
