"""Offline contract tests: no requests to Cornell or downloads of real recordings."""
import csv
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location('macaulay_collect', Path(__file__).parents[1] / 'tools/macaulay_collect.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def client(handler):
    result = m.PoliteClient('research@example.org', client=httpx.Client(transport=httpx.MockTransport(handler)))
    result.waits = []
    result.pause = lambda minimum=0: result.waits.append(minimum)
    return result


def test_matching_only_notes_and_exact_default_substrings():
    assert not m.matches('in flight', m.DEFAULT_TERMS)
    assert [hit['term'] for hit in m.matches('WING beats while flying', m.DEFAULT_TERMS)] == ['wing', 'fly', 'beat']
    assert m.matches('fight', m.DEFAULT_TERMS)[0]['term'] == 'fight'
    assert m.matches('wingless', ['wing'])  # Deliberate literal substring, not a claim of audible wings.


def test_saved_page_preserves_fields_and_embedded_json():
    html = '''<dl><dt>Media notes</dt><dd>Audible <b>wing beats</b> &amp; calls.</dd>
    <dt>Recordist</dt><dd>Jane Example</dd><dt>Equipment</dt><dd>Recorder A</dd></dl>
    <script type="application/ld+json">{"name":"example"}</script>
    <audio aria-label="ML123" src="https://cdn.download.ams.birds.cornell.edu/api/v2/asset/123/mp3"></audio>'''
    record = m.parse_page(html, '123')
    assert record['media_notes'] == 'Audible wing beats & calls.'
    assert record['recordist'] == 'Jane Example'
    assert record['page_fields']['Equipment'] == ['Recorder A']
    assert record['page_json'] == [{'name': 'example'}]
    assert record['audio_url'].endswith('/123/mp3')


def test_challenge_is_not_indexed():
    with pytest.raises(RuntimeError, match='Bot verification'):
        m.parse_page("<title>Making sure you're not a bot!</title>", '123')


def test_robots_disallow_stops_before_asset_request():
    requests = []
    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200, text='User-agent: *\nDisallow: /')
    c = client(handler)
    with pytest.raises(RuntimeError, match='disallows'):
        c.request('https://example.org/asset/123')
    assert requests == ['https://example.org/robots.txt']


def test_redirect_destination_robots_checked():
    requests = []
    def handler(request):
        requests.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text='User-agent: *\nDisallow: ' + ('/' if request.url.host == 'blocked.org' else ''))
        return httpx.Response(302, headers={'Location': 'https://blocked.org/audio'})
    with pytest.raises(RuntimeError, match='disallows'):
        client(handler).request('https://example.org/audio')
    assert 'https://blocked.org/audio' not in requests


@pytest.mark.parametrize('status', [401, 403])
def test_access_denied_not_retried(status):
    requests = []
    def handler(request):
        requests.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        return httpx.Response(status)
    with pytest.raises(RuntimeError, match='access denied'):
        client(handler).request('https://example.org/audio')
    assert len(requests) == 2


def test_rate_limit_retry_after():
    attempts = []
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        attempts.append(1)
        return httpx.Response(429, headers={'Retry-After': '120'}) if len(attempts) == 1 else httpx.Response(200)
    c = client(handler)
    assert c.request('https://example.org/audio').status_code == 200
    assert 120 in c.waits
    assert len(attempts) == 2


def test_download_and_checksum_resume(tmp_path):
    calls = []
    def handler(request):
        calls.append(str(request.url))
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        return httpx.Response(200, content=b'ID3sample', headers={'Content-Type': 'audio/mpeg'})
    c = client(handler)
    record = {'asset_id': '123', 'audio_url': 'https://example.org/audio'}
    m.download(c, record, tmp_path)
    assert (tmp_path / 'ML123.mp3').read_bytes() == b'ID3sample'
    m.download(c, record, tmp_path)
    assert len(calls) == 2
    (tmp_path / 'ML123.mp3').write_bytes(b'corrupted')
    m.download(c, record, tmp_path)
    assert len(calls) == 3
    assert not list(tmp_path.glob('*.part'))


@pytest.mark.parametrize('content,mime', [(b'<html>challenge</html>', 'text/html'), (b'<html>challenge</html>', 'audio/mpeg'), (b'', 'audio/mpeg')])
def test_non_audio_does_not_commit(tmp_path, content, mime):
    def handler(request):
        if request.url.path == '/robots.txt':
            return httpx.Response(404)
        return httpx.Response(200, content=content, headers={'Content-Type': mime})
    with pytest.raises(RuntimeError):
        m.download(client(handler), {'asset_id': '123', 'audio_url': 'https://example.org/audio'}, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_export_workflow_deduplication_raw_metadata_and_rematching(tmp_path):
    source = tmp_path / 'export.csv'
    source.write_text('ML Catalog Number,Common Name,Recordist,Media Notes,Unknown Field\n'
                      'ML123,Flycatcher,Example,Silent bird,keep me\n'
                      'ML456,Dove,Recorder,Clear WING beats,keep too\n'
                      'ML456,Dove,Recorder,Clear WING beats,duplicate\n'
                      'ML789,Swift,Someone,,unknown\n', encoding='utf-8-sig')
    out = tmp_path / 'out'
    assert m.main(['--csv', str(source), '--out', str(out)]) == 0
    with (out / 'candidates.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert [r['ML Catalog Number'] for r in rows] == ['ML456']
    record = json.loads((out / 'metadata/ML456.json').read_text())
    assert len(record['export_rows']) == 2
    assert record['export_rows'][0]['Unknown Field'] == 'keep too'
    assert 'Recorder' in record['citation']
    assert json.loads((out / 'metadata/ML789.json').read_text())['notes_status'] == 'missing_or_empty_review_required'
    assert not list((out / 'audio').iterdir())
    m.main(['--csv', str(source), '--out', str(out), '--terms', 'silent'])
    with (out / 'candidates.csv').open() as f:
        assert [r['ML Catalog Number'] for r in csv.DictReader(f)] == ['ML123']
    assert json.loads((out / 'run.json').read_text())['status'] == 'completed'


def test_unrecognized_export_fails_explicitly(tmp_path):
    source = tmp_path / 'wrong.csv'
    source.write_text('unrecognized,Media Notes\n123,wingbeats\n')
    with pytest.raises(ValueError, match='columns'):
        list(m.read_export(source))
