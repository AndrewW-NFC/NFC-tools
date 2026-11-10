"""A broad pulse's fine spectral texture must not obscure its rhythm."""

# Role: Regression coverage for the user-reported broad upper-band pulse miss.
# Dependencies: NumPy, pytest, wave, the production detector and research scanner.

import io
import wave
from pathlib import Path

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeat_accompaniment as a
from nfc_tools.analyzers.wingbeats import detect_stream


def recording(name='reported-wing-miss'):
    path = Path(__file__).parent / 'fixtures' / f'{name}.wav'
    with wave.open(str(path)) as audio:
        assert audio.getframerate() == a.ANALYSIS_RATE
        return np.frombuffer(audio.readframes(audio.getnframes()), dtype='<i2') / 32767


@pytest.mark.parametrize('name,end', [('reported-wing-miss', 42000),
                                    ('reported-wing-miss-purfin', 54000)])
def test_reported_miss_recovers_through_fixed_lobe_with_existing_gates(name, end):
    samples = recording(name)[18000:end]
    features = a.accompaniment_features(samples)
    assert a.screen_accompaniment([f for f in features if not f.fixed_lobe_envelope]) is None
    accepted = [f for f in features if a.screen_accompaniment([f]) is not None]
    assert accepted and all(f.fixed_lobe_envelope for f in accepted)
    assert all(a.localized_pulse_support(f) for f in accepted)
    assert all(not a.accompaniment_spectral_support(f) for f in accepted)


@pytest.mark.parametrize('gain', [.1, 1, 3])
@pytest.mark.parametrize('padding', [0, .07, .19, .25, .5, .75])
@pytest.mark.parametrize('name', ['reported-wing-miss', 'reported-wing-miss-purfin'])
def test_reported_miss_survives_gain_and_alignment(gain, padding, name, request):
    if name == 'reported-wing-miss-purfin' and padding in (.07, .19):
        request.node.add_marker(pytest.mark.xfail(
            strict=True, reason='Known alignment-sensitive miss in the second three-second crop'))
    samples = np.r_[np.zeros(round(padding * a.ANALYSIS_RATE)), recording(name) * gain]
    raw = samples.astype('<f4').tobytes()
    hits = detect_stream(io.BytesIO(raw), a.ANALYSIS_RATE)
    assert hits and any(hit.start < padding + 2 and hit.end > padding + .75 for hit in hits)


def test_fixed_lobe_cache_and_research_measurements_agree():
    from test_wingbeat_research import scan

    samples = recording()[18000:42000].astype('<f4')
    row = scan.instrument_window(samples, .75, pass_kind='brief')
    assert row['current_detect']
    assert row['acc_3500_6500_fixed_lobe_periodicity'] >= .6
    assert row['acc_3500_6500_fixed_lobe_failed_gates'] == ''
    raw = recording().astype('<f4').tobytes()
    assert detect_stream(io.BytesIO(raw), a.ANALYSIS_RATE) == detect_stream(
        io.BytesIO(raw), a.ANALYSIS_RATE, reuse_frames=False)
