"""Regression tests for BirdNET upgrade identity and mixed-version safeguards."""

# Role: Run by pytest to protect the behavior exercised by the tests below.
# Dependencies: pytest runs the tests. Project/external imports:
# nfc_tools.birdnet_version, nfc_tools.clip_exporter, nfc_tools.config,
# nfc_tools.importer, nfc_tools.installer, nfc_tools.night_status, nfc_tools.session,
# pytest.

import json

import pytest

from nfc_tools import birdnet_version, installer


def test_installer_never_reuses_or_changes_legacy_environment(tmp_path, monkeypatch):
    legacy = tmp_path / 'birdnet' / 'mamba'
    legacy.mkdir(parents=True)
    sentinel = legacy / 'keep.txt'
    sentinel.write_text('working 2.4 installation')
    monkeypatch.setattr(installer, 'analyzers_root', lambda: tmp_path)
    checked = []
    monkeypatch.setattr(installer, '_python_imports', lambda py, module: checked.append(py) or False)
    assert installer._working_birdnet_python() is None
    assert all('birdnet3' in path.parts for path in checked)
    assert sentinel.read_text() == 'working 2.4 installation'


@pytest.mark.parametrize('saved', [None, {'model': '2.4'}, {**birdnet_version.identity(), 'library': 'birdnet==0.0'}])
def test_old_or_changed_checkpoints_are_refused(tmp_path, saved):
    progress = {'files': {'old.wav': {'analyzers': {'birdnet': {
        'analysis': 'ok', 'birdnet_version': saved}}}}}
    original = json.dumps(progress)
    with pytest.raises(ValueError, match='fresh output folder'):
        birdnet_version.check_night(tmp_path, progress)
    assert json.dumps(progress) == original


def test_existing_results_without_checkpoint_are_protected(tmp_path):
    folder = tmp_path / 'results' / 'birdnet' / 'old'
    folder.mkdir(parents=True)
    result = folder / 'detections.csv'
    result.write_text('old results')
    with pytest.raises(ValueError, match='previous NFC Tools'):
        birdnet_version.check_night(tmp_path, {'files': {}})
    assert result.read_text() == 'old results'


def test_current_failed_analysis_can_resume(tmp_path):
    folder = tmp_path / 'results' / 'birdnet' / 'current'
    folder.mkdir(parents=True)
    (folder / 'partial.csv').touch()
    birdnet_version.check_night(tmp_path, {'files': {'current.wav': {'analyzers': {
        'birdnet': {'analysis': 'failed', 'birdnet_version': birdnet_version.identity()}}}}})


def test_old_import_cannot_start_or_change_checkpoint(tmp_path):
    from nfc_tools.importer import ImportRunner
    from nfc_tools.config import Config
    from uuid import uuid4
    cfg = Config()
    cfg.analyzers.enabled = ['birdnet']
    job = {'id': str(uuid4()), 'output': str(tmp_path), 'config': cfg.model_dump(),
           'state': 'paused'}
    runner = ImportRunner(job)
    with pytest.raises(ValueError, match='fresh output folder'):
        runner.start()
    assert job['state'] == 'paused'
    assert runner.thread is None


def test_session_refuses_legacy_recovery_before_export(tmp_path, monkeypatch):
    import wave
    from nfc_tools import night_status, clip_exporter
    from nfc_tools.config import Config
    from nfc_tools.session import Session
    wav = tmp_path / 'audio' / '001_NFC_2026-11-03_03-30-00.wav'
    wav.parent.mkdir()
    with wave.open(str(wav), 'wb') as audio:
        audio.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        audio.writeframes(b'\0\0' * 8000)
    progress = night_status.load_progress(tmp_path)
    entry = night_status.file_progress(tmp_path, wav, progress)
    entry['analyzers']['birdnet'] = {'analysis': 'ok', 'clips': 'pending'}
    night_status.save_progress(tmp_path, progress)
    before = (tmp_path / 'logs/analysis_progress.json').read_bytes()
    monkeypatch.setattr(clip_exporter, 'export_analyzer_clips',
                        lambda *args: pytest.fail('Must not export legacy results'))
    cfg = Config()
    cfg.analyzers.enabled = ['birdnet']
    session = Session(cfg)
    try:
        with pytest.raises(ValueError, match='fresh output folder'):
            session._analyze_one(wav)
        assert not session.status['analysis']['active']
        assert (tmp_path / 'logs/analysis_progress.json').read_bytes() == before
    finally:
        session._pool.shutdown()
