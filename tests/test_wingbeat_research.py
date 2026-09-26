"""Research sidecar contract: production sources stay untouched."""
import csv
import importlib.util
import io
import wave
from pathlib import Path

import numpy as np
import pytest

from nfc_tools.analyzers import wingbeats as production
from nfc_tools.analyzers.wingbeat_accompaniment import (
    ANALYSIS_RATE,
    accompaniment_features,
    distinct_pulses,
)

spec = importlib.util.spec_from_file_location('research_scan', Path(__file__).parents[1] / 'tools/wingbeat_research_scan.py')
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


def signal(kind, count=48000):
    t = np.arange(count) / ANALYSIS_RATE
    noise = np.random.default_rng(10).normal(0, .04, count)
    pulse = .03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    if kind == 'broadband':
        x = noise * pulse
    elif kind == 'accompaniment':
        spectrum = np.fft.rfft(noise) if count else np.array([])
        if count:
            spectrum[np.fft.rfftfreq(count, 1 / ANALYSIS_RATE) < 3500] = 0
            noise = np.fft.irfft(spectrum, n=count)
        x = (.2 * np.sin(2 * np.pi * 5432.1 * t) + noise) * pulse
    elif kind == 'tone':
        x = .2 * np.sin(2 * np.pi * 5432.1 * t) * pulse
    elif kind == 'nan':
        x = np.full(count, np.nan)
    else:
        x = np.zeros(count)
    return x.astype('<f4')


@pytest.mark.parametrize('kind', ['broadband', 'accompaniment', 'tone', 'silence', 'nan'])
def test_decision_route_and_no_mutation(kind):
    samples = signal(kind)
    saved = samples.copy()
    before = production.screen_window(samples, ANALYSIS_RATE)
    row = scan.instrument_window(samples, 0.)
    after = production.screen_window(samples, ANALYSIS_RATE)
    assert before == after
    assert row['current_detect'] == int(before is not None)
    assert row['current_score'] == (before if before is not None else '')
    assert row['current_route'] == (kind if kind in ('broadband', 'accompaniment') else 'none')
    np.testing.assert_array_equal(samples, saved)
    assert scan.fast_accompaniment_features is accompaniment_features
    if row.get('best_lag_frames'):
        count = sum(row[f'band{i}_{low}_{high}_coherence'] >= .60 and
                    row[f'band{i}_{low}_{high}_repetition'] >= .35 and
                    row[f'band{i}_{low}_{high}_modulation'] >= .15
                    for i, (low, high) in enumerate(production.PULSE_BANDS, 1))
        assert count == row['wing_coherent_bands']
        assert row['research_pulse_count'] == row['wing_pulse_count']


@pytest.mark.parametrize('n', [0, 23999, 24000, 47999, 48000, 48001, 72000, 79201, 96000])
@pytest.mark.parametrize('kind', ['broadband', 'accompaniment'])
def test_exact_stream_windows_and_candidates(n, kind, monkeypatch):
    samples = signal(kind, n)
    visited = []
    screen = production.screen_window
    def observe(x, sr, **kwargs):
        visited.append(x.copy())
        return screen(x, sr, **kwargs)
    monkeypatch.setattr(production, 'screen_window', observe)
    reference = production.detect_stream(io.BytesIO(samples.tobytes()), ANALYSIS_RATE)
    windows = list(scan.window_slices(samples))
    assert len(windows) == len(visited)
    for (_, chunk, _), observed in zip(windows, visited):
        np.testing.assert_array_equal(chunk, observed)
    rows = [scan.instrument_window(x, start, kind) for start, x, kind in windows]
    assert scan.compare_candidates(reference, scan.merged_from_rows(rows))


def test_merge_separate_touching_events_and_exact_comparison():
    rows = [{'current_detect': 1, 'window_start_sec': a, 'window_end_sec': b, 'current_score': c}
            for a, b, c in [(0., 2., .8), (2., 4., .9), (5., 7.000041666666667, .7)]]
    assert scan.merged_from_rows(rows) == [(0., 4., .9), (5., 7.000041666666667, .7)]
    assert not scan.compare_candidates([(0, 1, .8)], [(0, 1.000001, .8)])
    assert not scan.compare_candidates([(0, 1, .8)], [(0, 1, float('nan'))])


@pytest.mark.parametrize('period', [5, 14, 49])
def test_pulse_selection_matches_production(period):
    env = np.random.default_rng(4).uniform(size=197)
    assert len(scan._select_pulse_peaks(env, .6, period)) == distinct_pulses(env, .6, period)


def test_decoder_and_file_validation(tmp_path):
    source = tmp_path / 'stereo.wav'
    x = signal('accompaniment', 72001)
    with wave.open(str(source), 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(ANALYSIS_RATE)
        pcm = (x * 32767).astype('<i2')
        f.writeframes(np.column_stack([pcm, pcm]).tobytes())
    decoded = scan.decode_audio(source)
    assert len(decoded) == len(x)
    out = tmp_path / 'per_file' / 'stereo.csv'
    result = scan._process_one_file(str(source), str(out), {}, 'test', True)
    assert result['reference_validation_match'] == 1
    with out.open() as f:
        rows = list(csv.DictReader(f))
    assert scan.compare_candidates(production.detect_stream(io.BytesIO(decoded.tobytes()), ANALYSIS_RATE), scan.merged_from_rows(rows))
    assert rows[0]['meta_source_channels'] == '2'
    assert rows[-1]['window_end_sec'] == str(len(x) / ANALYSIS_RATE)


def test_consolidate_union_for_invalid_short_windows(tmp_path):
    per = tmp_path / 'parts'
    scan.write_csv_atomic(per / 'a.csv', [scan.instrument_window(np.zeros(2, dtype='<f4'), 0.)])
    scan.write_csv_atomic(per / 'b.csv', [scan.instrument_window(signal('broadband'), 1.)])
    scan.consolidate(per, tmp_path / 'all.csv')
    with (tmp_path / 'all.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]['beat_rate_hz'] == ''
    assert rows[1]['current_route'] == 'broadband'


def test_mismatch_is_fatal_and_not_published(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, 'decode_audio', lambda p: signal('broadband'))
    monkeypatch.setattr(scan, 'compare_candidates', lambda a, b: False)
    source = tmp_path / 'fake.mp3'
    source.write_bytes(b'placeholder')
    out = tmp_path / 'per_file' / 'fake.csv'
    with pytest.raises(RuntimeError, match='DECISION MISMATCH'):
        scan._process_one_file(str(source), str(out), {}, 'test', True)
    assert not out.exists()


def test_interrupted_validation_never_publishes_final(tmp_path, monkeypatch):
    monkeypatch.setattr(scan, 'decode_audio', lambda p: signal('broadband'))
    def interrupted(*args):
        raise KeyboardInterrupt()
    monkeypatch.setattr(scan, 'detect_stream', interrupted)
    source = tmp_path / 'fake.mp3'
    source.write_bytes(b'placeholder')
    out = tmp_path / 'per_file' / 'fake.csv'
    with pytest.raises(KeyboardInterrupt):
        scan._process_one_file(str(source), str(out), {}, 'test', True)
    assert not out.exists()
    # Checkpoint is retained so validation will run again after resumption.
    assert list((out.parent / '_parts' / 'fake').glob('part_*.csv'))


def test_partial_checkpoint_resumes_exactly(tmp_path, monkeypatch):
    source = tmp_path / 'fake.mp3'
    source.write_bytes(b'placeholder')
    samples = np.zeros(202 * ANALYSIS_RATE + 1, dtype='<f4')
    monkeypatch.setattr(scan, 'decode_audio', lambda p: samples)
    def measure(chunk, start, kind="standard"):
        return {'window_start_sec': start, 'window_end_sec': start + len(chunk)/ANALYSIS_RATE,
                    'current_detect': 0, 'current_score': ''}
    monkeypatch.setattr(scan, 'instrument_window', measure)
    out = tmp_path / 'per_file' / 'fake.csv'
    parts = out.parent / '_parts' / 'fake'
    windows = list(scan.window_slices(samples))
    base = {'source': 'test', 'file_id': 'fake', 'filename': 'fake.mp3', 'reference_validation_match': ''}
    scan.write_csv_atomic(parts / 'part_000000.csv', [{**base, **measure(c, t, k)} for t, c, k in windows[:200]])
    scan.write_csv_atomic(parts / 'part_000001.csv', [{**base, **measure(c, t, k)} for t, c, k in windows[200:201]])
    result = scan._process_one_file(str(source), str(out), {}, 'test', False)
    assert result['windows'] == len(windows)
    with out.open() as f:
        rows = list(csv.DictReader(f))
    assert [float(r['window_start_sec']) for r in rows] == [t for t, _, _ in windows]


@pytest.mark.parametrize('field,threshold', [
    ('peak_envelope', 1e-4), ('spectral_flatness', .12), ('modulation', .25),
    ('periodicity', .60), ('repeat_periodicity', .35), ('pulse_count', 4),
    ('coherent_bands', 3), ('band_energy_fraction', 1e-4),
    ('low_band_fraction', .005),
])
@pytest.mark.parametrize('side', ['below', 'at', 'above'])
def test_route_labels_at_exact_production_gate_boundaries(field, threshold, side, monkeypatch):
    from dataclasses import replace

    base = production.WindowFeatures(.5, .8, .9, .8, 8, 1., 4, .9, .15)
    value = threshold if side == 'at' else np.nextafter(threshold, -np.inf if side == 'below' else np.inf)
    measured = replace(base, **{field: value})
    monkeypatch.setattr(production, 'window_features', lambda *args: measured)
    monkeypatch.setattr(production, 'accompaniment_features', lambda *args: [])
    expected = production.screen_window(np.zeros(48000), ANALYSIS_RATE) is not None
    assert scan._current_broadband_pass(measured) == expected
    failures, _, _, passed, _ = scan._gate_failures(measured, [])
    assert passed == expected
    assert (field in failures.split(';')) == (side == 'below')


def test_complete_stream_with_separated_routes():
    samples = np.concatenate([signal('broadband'), signal('silence', 96000),
                              signal('accompaniment'), signal('silence', 10001)])
    reference = production.detect_stream(io.BytesIO(samples.tobytes()), ANALYSIS_RATE)
    rows = [scan.instrument_window(x, start, kind) for start, x, kind in scan.window_slices(samples)]
    assert len(reference) == 2
    assert {'broadband', 'accompaniment'} <= {r['current_route'] for r in rows}
    assert scan.compare_candidates(reference, scan.merged_from_rows(rows))
