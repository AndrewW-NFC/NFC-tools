import hashlib
import json
import threading
import wave
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from nfc_tools import importer, manifest
from nfc_tools.analyzers.base import AnalyzerResult
from nfc_tools.config import Config
from nfc_tools.web import routes_import
from nfc_tools.web.server import create_app


@pytest.fixture
def setup_import(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    output = tmp_path / 'output'
    source.mkdir()
    output.mkdir()
    wav = source / '2026-08-08_23-59-58.wav'
    with wave.open(str(wav), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b'\0\0' * 8000 * 4)
    cfg = Config()
    cfg.advanced.keep_awake = False
    cfg.analyzers.enabled = ['nighthawk']
    calls = []

    def run(path, out, used_cfg):
        calls.append((path, used_cfg.model_copy(deep=True)))
        out.mkdir(parents=True, exist_ok=True)
        (out / 'test_audacity.txt').write_text('0\t1\tswathr (0.943)\n')
        return AnalyzerResult('nighthawk', True, out)

    monkeypatch.setattr(importer.analyzers, 'get', lambda name: SimpleNamespace(run=run))
    monkeypatch.setattr(routes_import.state, 'cfg', cfg)
    manager = importer.ImportManager()
    monkeypatch.setattr(routes_import, 'manager', manager)
    client = TestClient(create_app())
    scan = client.post('/import-recordings/scan', data={'source_folder': str(source), 'output_folder': str(output)}).json()
    data = scan['source']['review_files'][0]
    request = dict(request_id=str(uuid4()), source_folder=str(source), output_folder=str(output),
                   site_name='Imported site', latitude=42, longitude=-71, timezone='America/New_York',
                   timeline_confirmed=True, storage_confirmed=True,
                   files=[dict(relative_path=data['relative_path'], start='2026-08-08T23:59:58',
                               size_bytes=data['size_bytes'], mtime_ns=data['mtime_ns'])])
    return SimpleNamespace(source=source, output=output, wav=wav, cfg=cfg, calls=calls,
                           manager=manager, client=client, request=request)


def join(manager):
    manager.runner.thread.join(timeout=15)
    assert not manager.runner.thread.is_alive()
    return manager.runner.status()


def test_import_real_conversion_analysis_clips_and_idempotent_start(setup_import):
    s = setup_import
    original = hashlib.sha256(s.wav.read_bytes()).digest()
    response = s.client.post('/import-recordings/start', json=s.request)
    assert response.status_code == 200, response.text
    status = join(s.manager)
    assert status['state'] == 'complete', status
    assert status['completed_segments'] == 2
    audio = sorted(s.output.glob('*/audio/*.wav'))
    assert len(audio) == 2
    assert audio[0].name.endswith('2026-08-08_23-59-58.wav')
    assert audio[1].name.endswith('2026-08-09_00-00-00.wav')
    assert all(path.parent.parent.name == '2026-08-08' for path in audio)
    for path in audio:
        session = importer.Session(s.cfg)
        try:
            converted = session._read_wav_header(path)
            assert (converted['sample_rate'], converted['channels'], converted['bits_per_sample']) == (48000, 1, 32)
            assert converted['duration_seconds'] == 2
        finally:
            session._pool.shutdown()
    assert len(s.calls) == 2
    assert s.calls[0][1].site.name == 'Imported site'
    assert s.cfg.site.name != 'Imported site'
    assert len(list(s.output.glob('*/clips/*/*.wav'))) == 2
    assert any(row['recorded_date'] == '2026-08-09' for row in manifest.read_all(audio[0].parent.parent))
    assert hashlib.sha256(s.wav.read_bytes()).digest() == original
    assert s.client.post('/import-recordings/start', json=s.request).json()['job']['state'] == 'complete'
    assert len(s.calls) == 2


def test_pause_and_recover_checkpoint_skips_completed_segments(setup_import, monkeypatch):
    s = setup_import
    original = importer.ImportRunner.process_segment

    def pause_after_segment(self, session):
        original(self, session)
        self.pause()

    monkeypatch.setattr(importer.ImportRunner, 'process_segment', pause_after_segment)
    s.client.post('/import-recordings/start', json=s.request)
    assert join(s.manager)['state'] == 'paused'
    assert len(s.calls) == 1
    monkeypatch.setattr(importer.ImportRunner, 'process_segment', original)
    recovered = importer.ImportManager()
    runner = recovered.recover(str(s.output), s.manager.runner.job['id'])
    runner.start()
    assert join(recovered)['state'] == 'complete'
    assert len(s.calls) == 2
    assert len(list(s.output.glob('*/audio/*.wav'))) == 2


def test_analysis_failure_is_retryable_without_reconverting(setup_import, monkeypatch):
    s = setup_import
    original = importer.Session._analyze_one
    monkeypatch.setattr(importer.Session, '_analyze_one', lambda *args: {'nighthawk': 'failed'})
    s.client.post('/import-recordings/start', json=s.request)
    assert join(s.manager)['state'] == 'failed'
    wav = next(s.output.glob('*/audio/*.wav'))
    timestamp = wav.stat().st_mtime_ns
    monkeypatch.setattr(importer.Session, '_analyze_one', original)
    response = s.client.post(f"/import-recordings/run/{s.request['request_id']}/resume", data={'output': str(s.output)})
    assert response.status_code == 200
    assert join(s.manager)['state'] == 'complete'
    assert wav.stat().st_mtime_ns == timestamp


@pytest.mark.parametrize('change', ['confirmation', 'missing_file', 'changed_file', 'outside', 'nested_output', 'timezone', 'empty_analyzers'])
def test_start_rejects_invalid_plan_without_creating_archive(setup_import, change):
    s = setup_import
    if change == 'confirmation':
        s.request['storage_confirmed'] = False
    elif change == 'missing_file':
        (s.source / 'new.wav').write_bytes(b'new')
    elif change == 'changed_file':
        s.wav.write_bytes(b'changed')
    elif change == 'outside':
        s.request['files'][0]['relative_path'] = '../outside.wav'
    elif change == 'nested_output':
        s.request['output_folder'] = str(s.source)
    elif change == 'timezone':
        s.request['timezone'] = 'Invalid/Zone'
    else:
        s.cfg.analyzers.enabled = []
    response = s.client.post('/import-recordings/start', json=s.request)
    assert response.status_code == 400, response.text
    assert not list(s.output.iterdir())


def test_low_space_uses_pcm_size(setup_import, monkeypatch):
    s = setup_import
    monkeypatch.setattr(importer.shutil, 'disk_usage', lambda path: SimpleNamespace(free=100000))
    response = s.client.post('/import-recordings/start', json=s.request)
    assert response.status_code == 400
    assert 'Insufficient' in response.json()['error']


def test_existing_archive_audio_is_not_overwritten(setup_import):
    s = setup_import
    audio = s.output / '2026-08-08' / 'audio'
    audio.mkdir(parents=True)
    old = audio / '001_NFC_2026-08-08_23-59-58.wav'
    old.write_bytes(b'keep me')
    s.client.post('/import-recordings/start', json=s.request)
    assert join(s.manager)['state'] == 'complete'
    assert old.read_bytes() == b'keep me'
    assert len(list(audio.glob('*.wav'))) == 3


def test_only_one_running_import(setup_import, monkeypatch):
    s = setup_import
    entered, release = threading.Event(), threading.Event()
    original = importer.ImportRunner.process_segment

    def block(self, session):
        entered.set()
        assert release.wait(10)
        return original(self, session)

    monkeypatch.setattr(importer.ImportRunner, 'process_segment', block)
    s.client.post('/import-recordings/start', json=s.request)
    assert entered.wait(5)
    try:
        second = {**s.request, 'request_id': str(uuid4())}
        response = s.client.post('/import-recordings/start', json=second)
        assert response.status_code == 400
        assert 'already running' in response.json()['error']
        pause = s.client.post(f"/import-recordings/run/{s.request['request_id']}/pause", data={'output': str(s.output)})
        assert pause.json()['job']['pause_requested'] is True
    finally:
        release.set()
        join(s.manager)


def test_dst_interpretation_and_elapsed_duration():
    zone = ZoneInfo('America/New_York')
    with pytest.raises(ValueError, match='does not exist'):
        importer.local_start(datetime(2026, 3, 8, 2, 30), zone, 'earlier')
    value = datetime(2026, 11, 1, 1, 30)
    earlier = importer.local_start(value, zone, 'earlier')
    later = importer.local_start(value, zone, 'later')
    assert later.timestamp() - earlier.timestamp() == 3600
    cfg = Config()
    # A 1-hour segment remains 3600 seconds even when the local clock repeats.
    assert importer.segment_details(earlier, 7200, cfg)[2] == 3600


def test_checkpoint_retains_corrected_start(setup_import):
    s = setup_import
    s.request['files'][0]['start'] = '2026-08-09T03:30:00'
    s.client.post('/import-recordings/start', json=s.request)
    assert join(s.manager)['state'] == 'complete'
    job = json.loads(next(s.output.glob('.nfc-imports/*/job.json')).read_text())
    assert job['files'][0]['start'] == '2026-08-09T03:30:00-04:00'
    assert next(s.output.glob('*/audio/*.wav')).name.endswith('2026-08-09_03-30-00.wav')
