"""Call rejection must preserve abrupt wingbeats and the guarded field control."""

import io
from dataclasses import replace

import pytest

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream
from test_wingbeat_fixed_lobe import recording
from test_wingbeat_call_motion import ROWS


def hits(samples, *, reuse_frames=True):
    return detect_stream(io.BytesIO(samples.astype('<f4').tobytes()),
                         a.ANALYSIS_RATE, reuse_frames=reuse_frames)


@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_reported_robin_rejected_without_losing_abrupt_wings(gain, monkeypatch):
    robin = recording('robin-strong-sweep') * gain
    wings = recording('abrupt-wingbeat') * gain
    assert not hits(robin)
    expected = hits(wings)
    assert expected and expected[0].start == 0 and expected[-1].end == 2
    # Restore only the previous rejection boundary, leaving all other gates
    # unchanged: the reported robin must reproduce its former false positive.
    monkeypatch.setattr(a, 'MAX_STRONG_SWEEP_LOW_BAND_FRACTION', .0005)
    assert hits(robin)
    assert hits(wings) == expected


def test_new_motion_measurements_agree_with_uncached_screening():
    for name in ('robin-strong-sweep', 'abrupt-wingbeat'):
        samples = recording(name)
        assert hits(samples) == hits(samples, reuse_frames=False)


def test_smaller_sweep_keeps_original_bass_protection():
    row = next(r for r in ROWS if r['id'] == 'field-1078-1-0:1.25:3500')
    field = a.AccompanimentFeatures(**row['features'])
    assert .0005 <= field.low_band_fraction < .001
    assert 700 <= field.pulse_centroid_range_hz < 1000
    assert not a.swept_call_interference(field)
    assert a.screen_accompaniment([field], allow_near_miss=True) is not None
    assert a.swept_call_interference(replace(field, pulse_centroid_range_hz=1000))
    assert not a.swept_call_interference(replace(
        field, pulse_centroid_range_hz=1000, low_band_fraction=.001))
