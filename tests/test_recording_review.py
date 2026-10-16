import csv
import io
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from nfc_tools.review.server import create_app

HEADERS = {'X-Review-Client': 'local-review'}


@pytest.fixture
def workspace(tmp_path):
    batch = tmp_path / 'reviews/test'
    batch.mkdir(parents=True)
    audio = tmp_path / 'audio-library/test.wav'
    audio.parent.mkdir()
    audio.write_bytes(b'RIFF' + b'\x00' * 100)
    record = dict(id='ml-123', catalog_number='123', species='Mallard', recordist='A', source_notes='', duration=10,
                  source_sha256='original', preview_sha256='preview', audio_path='audio-library/test.wav', peaks=[0, .5])
    (batch / 'batch.json').write_text(json.dumps(dict(batch_id='test', records=[record])))
    return tmp_path, batch


def review(**kwargs):
    return dict(revision=0, reviewer='Listener', status='in_progress', outcome='unreviewed', intervals=[],
                listened=[], full_listen_confirmed=False, interference=[], notes='', **kwargs) if not kwargs else {
                    **review(), **kwargs}


def test_partial_negative_cannot_be_complete(workspace):
    client = TestClient(create_app(*workspace))
    data = review(status='complete', outcome='absent', listened=[[0, 3]])
    r = client.post('/api/reviews/ml-123', json=data, headers=HEADERS)
    assert r.status_code == 422
    assert not client.get('/api/batch').json()['reviews']
    data['status'] = 'in_progress'
    assert client.post('/api/reviews/ml-123', json=data, headers=HEADERS).status_code == 200


def test_revisions_backups_reload_conflicts_and_exports(workspace):
    root, batch = workspace
    client = TestClient(create_app(root, batch))
    data = review(status='complete', outcome='present', listened=[[0, 6], [5, 10]],
                  intervals=[dict(start=1.25, end=3.5, confidence='faint', note='With calls')])
    first = client.post('/api/reviews/ml-123', json=data, headers=HEADERS)
    assert first.status_code == 200
    assert first.json()['reviewed_seconds'] == 10
    assert first.json()['revision'] == 1
    assert client.post('/api/reviews/ml-123', json=data, headers=HEADERS).status_code == 409
    data.update(revision=1, notes='A second listen')
    assert client.post('/api/reviews/ml-123', json=data, headers=HEADERS).json()['revision'] == 2
    restored = TestClient(create_app(root, batch))
    assert restored.get('/api/batch').json()['reviews']['ml-123']['notes'] == 'A second listen'
    assert len(list((batch / 'backups').glob('*.json'))) == 2
    with sqlite3.connect(batch / 'annotations.sqlite') as conn:
        assert conn.execute('select count(*) from revisions').fetchone()[0] == 2
    rows = list(csv.DictReader(io.StringIO(restored.get('/api/export/passages').text)))
    assert rows[0]['start_seconds'] == '1.25'
    assert rows[0]['source_sha256'] == 'original'
    assert restored.get('/api/export/json').json()['reviews']['ml-123']['revision'] == 2


@pytest.mark.parametrize('changes', [
    dict(outcome='absent', intervals=[dict(start=1, end=2)]),
    dict(intervals=[dict(start=4, end=3)]),
    dict(intervals=[dict(start=0, end=11)]),
    dict(listened=[[3, 2]]),
    dict(listened=[[0, 11]]),
    dict(status='complete', outcome='present', full_listen_confirmed=True),
    dict(reviewer='   '),
])
def test_invalid_annotations_rejected(workspace, changes):
    client = TestClient(create_app(*workspace))
    assert client.post('/api/reviews/ml-123', json=review(**changes), headers=HEADERS).status_code == 422


def test_manual_full_listen_is_explicit_and_persisted(workspace):
    client = TestClient(create_app(*workspace))
    r = client.post('/api/reviews/ml-123', json=review(status='complete', outcome='absent', full_listen_confirmed=True), headers=HEADERS)
    assert r.status_code == 200
    assert r.json()['full_listen_confirmed'] is True
    assert r.json()['listened'] == []
    assert r.json()['reviewed_seconds'] == 10
    data = review(revision=1, status='complete', outcome='absent')
    assert client.post('/api/reviews/ml-123', json=data, headers=HEADERS).status_code == 422


def test_audio_range_and_local_request_boundaries(workspace):
    client = TestClient(create_app(*workspace))
    assert client.get('/audio/ml-123', headers={'Range': 'bytes=0-3'}).content == b'RIFF'
    assert client.get('/audio/not-in-batch').status_code == 404
    assert client.post('/api/reviews/ml-123', json=review()).status_code == 403
    assert client.post('/api/reviews/ml-123', json=review(), headers={**HEADERS, 'Origin': 'https://elsewhere.example'}).status_code == 403
    assert client.get('/api/batch', headers={'Host': 'elsewhere.example'}).status_code == 403


def test_backup_failure_does_not_commit(workspace, monkeypatch):
    client = TestClient(create_app(*workspace), raise_server_exceptions=False)
    original = Path.open
    def fail_backup(path, *args, **kwargs):
        if path.parent.name == 'backups':
            raise OSError('Drive write failed')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail_backup)
    assert client.post('/api/reviews/ml-123', json=review(), headers=HEADERS).status_code == 500
    assert not client.get('/api/batch').json()['reviews']
