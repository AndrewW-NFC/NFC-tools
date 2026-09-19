import csv
import io
import wave

import numpy as np
import pytest

from nfc_tools.analyzers import get
from nfc_tools.analyzers.wingbeats import SAMPLE_RATE, detect_stream, screen_window
from nfc_tools.clip_exporter import _clip_specs, export_analyzer_clips
from nfc_tools.config import Config
from nfc_tools.ebird_export import (
    _night_detections, _aggregate_detections_for_import,
    EbirdExportOptions, prepare_record_export,
)
from nfc_tools.readiness import _check_analyzers


def pulse_train(seconds=4, rate=7):
    t = np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE
    noise = np.random.default_rng(10).normal(0, 0.15, len(t))
    envelope = 0.02 + np.maximum(0, np.sin(2 * np.pi * rate * t)) ** 4
    return (noise * envelope).astype('<f4')


@pytest.mark.parametrize('rate', [3, 7, 12, 18])
def test_flags_repeated_broadband_pulses(rate):
    assert screen_window(pulse_train(rate=rate)) is not None


@pytest.mark.parametrize('kind', ['silence', 'noise', 'tone', 'impulse', 'rumble', 'short', 'nan'])
def test_rejects_non_candidates(kind):
    t = np.arange(SAMPLE_RATE * 4) / SAMPLE_RATE
    samples = np.zeros(len(t), dtype='<f4')
    if kind == 'noise':
        samples = np.random.default_rng(42).normal(0, 0.1, len(t))
    elif kind == 'tone':
        samples = np.sin(2 * np.pi * 1000 * t) * (0.1 + np.maximum(0, np.sin(2 * np.pi * 7 * t)))
    elif kind == 'impulse':
        samples[12000:12020] = 1
    elif kind == 'rumble':
        samples = np.sin(2 * np.pi * 40 * t)
    elif kind == 'short':
        samples = pulse_train(0.3)
    elif kind == 'nan':
        samples[:] = np.nan
    assert screen_window(samples) is None


def test_stream_merges_windows_and_handles_tail():
    signal = pulse_train(9.3)
    detections = detect_stream(io.BytesIO(signal.tobytes()))
    assert len(detections) == 1
    assert detections[0].start == 0
    assert detections[0].end == pytest.approx(9.3)


def test_truncated_stream_fails():
    with pytest.raises(ValueError, match='Truncated'):
        detect_stream(io.BytesIO(b'bad'))


def test_plugin_results_clips_and_review_only(tmp_path):
    night = tmp_path / '2026-09-19'
    wav = night / 'audio' / '001_NFC_2026-09-19_01-00-00.wav'
    wav.parent.mkdir(parents=True)
    # Stereo 16-bit input exercises real decoding/resampling.
    samples = (pulse_train(6) * 32767).astype('<i2')
    with wave.open(str(wav), 'wb') as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(np.column_stack([samples, samples]).tobytes())
    out = night / 'results' / 'wingbeats' / wav.stem
    result = get('wingbeats').run(wav, out, Config())
    assert result.success, result.message
    assert result.detections_count == 1
    specs = _clip_specs('wingbeats', out, Config())
    assert len(specs) == 1
    assert specs[0].label == 'WING (review required)'
    assert specs[0].analyzer_label == 'Wingbeats'
    detections = _night_detections(night)
    assert len(detections) == 1
    assert detections[0].source_label == 'WING'
    assert detections[0].confidence is None
    assert not detections[0].contributes_nfc_count
    assert not _aggregate_detections_for_import(detections)
    assert export_analyzer_clips(wav, 'wingbeats', out, night / 'clips', Config()) == 1
    assert len(list((night / 'clips').rglob('WING*-Wingbeats.wav'))) == 1
    prepare_record_export(night, EbirdExportOptions(
        location_name='Test', latitude=42.4, longitude=-71.1, state_province='MA',
    ))
    reviews = list((night / 'eBird checklists').glob('ebird_review_*.csv'))
    assert reviews
    with reviews[0].open(encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]['source_label'] == 'WING'
    assert 'manual review required' in rows[0]['species_comments']
    assert rows[0]['max_confidence'] == ''
    for path in (night / 'eBird checklists').glob('ebird_record_import_*.csv'):
        assert path.read_text() == ''
    # Reanalysis with silence clears previous output.
    with wave.open(str(wav), 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(b'\0\0' * SAMPLE_RATE * 2)
    result = get('wingbeats').run(wav, out, Config())
    assert result.success and result.detections_count == 0
    assert not _clip_specs('wingbeats', out, Config())


def test_decode_failure_is_reported(tmp_path):
    result = get('wingbeats').run(tmp_path / 'missing.wav', tmp_path / 'out', Config())
    assert not result.success
    assert not list((tmp_path / 'out').glob('*.csv'))


def test_builtin_needs_no_model_install(monkeypatch):
    monkeypatch.setattr('nfc_tools.readiness.installer.status', lambda: {})
    cfg = Config()
    cfg.analyzers.enabled = ['wingbeats']
    assert 'Enabled analyzers are ready' in _check_analyzers(cfg).detail


@pytest.mark.parametrize('seed', range(10))
def test_detects_low_contrast_pulses_against_background(seed):
    t = np.arange(16000) / SAMPLE_RATE
    noise = np.random.default_rng(seed).normal(0, .1, len(t))
    signal = noise * (1 + .25 * np.sin(2 * np.pi * 7 * t))
    assert screen_window(signal) is not None


@pytest.mark.parametrize('seed', range(10))
def test_rejects_sweeping_tonal_calls_with_noise(seed):
    t = np.arange(16000) / SAMPLE_RATE
    background = np.random.default_rng(seed).normal(0, .002, len(t))
    signal = background + .2 * np.sin(2 * np.pi * (1500 * t + 1000 * t * t)) * np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    assert screen_window(signal) is None


@pytest.mark.parametrize('kind', ['pink', 'wind', 'swell'])
@pytest.mark.parametrize('seed', range(5))
def test_rejects_colored_noise_and_single_swell(kind, seed):
    t = np.arange(16000) / SAMPLE_RATE
    signal = np.random.default_rng(seed).normal(0, .1, len(t))
    if kind == 'swell':
        signal *= .1 + np.exp(-((t - 1) / .3) ** 2)
    else:
        freq = np.fft.rfftfreq(len(signal), 1 / SAMPLE_RATE)
        signal = np.fft.irfft(np.fft.rfft(signal) / np.maximum(freq, 1) ** (.5 if kind == 'pink' else 1), n=len(signal))
    assert screen_window(signal) is None
