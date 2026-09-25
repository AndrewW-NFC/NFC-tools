import asyncio
import pytest
from nfc_tools.config import Site
from nfc_tools.ebird_export import options_for_site
from nfc_tools import ebird_locations


def test_site_opt_out_and_legacy_defaults():
    assert Site().exports_enabled
    assert Site(ebird_export_enabled=None).exports_enabled
    assert not Site(ebird_export_enabled=False).exports_enabled
    assert Site(ebird_state_province='MA').exports_enabled
    assert not Site(ebird_state_province='MA', ebird_export_enabled=False).exports_enabled


def test_canonical_hotspot_keeps_recording_coordinates(monkeypatch):
    hotspot = dict(locId='L123', locName='Official name', lat=43, lng=-72)
    monkeypatch.setattr(ebird_locations, '_hotspots', {'L123': hotspot})
    site = Site(name='My backyard recorder', latitude=42, longitude=-71, ebird_state_province='MA', ebird_location_type='hotspot')
    site.ebird_hotspot_details = ebird_locations.selected_hotspot('L123', site)
    options = options_for_site(site)
    assert (options.location_name, options.latitude, options.longitude) == ('Official name', 43, -72)
    assert (site.name, site.latitude, site.longitude) == ('My backyard recorder', 42, -71)
    with pytest.raises(ValueError):
        ebird_locations.selected_hotspot('L999', site)


def test_lookup_requires_key(monkeypatch):
    monkeypatch.delenv('EBIRD_API_KEY', raising=False)
    with pytest.raises(ValueError, match='API key'):
        asyncio.run(ebird_locations.nearby_hotspots(42, -71, ''))


@pytest.mark.parametrize("enabled, expected", [(None, True), (True, True), (False, False)])
def test_location_checkbox_reflects_serialized_settings(enabled, expected):
    from nfc_tools.config import Config
    from nfc_tools.web.routes import templates

    cfg = Config(site=Site(ebird_export_enabled=enabled))
    html = templates.env.get_template("ebird_location.html").render(
        cfg=cfg.model_dump(), location_prefix=""
    )
    checkbox = next(line for line in html.splitlines() if 'type="checkbox"' in line)
    details = next(line for line in html.splitlines() if 'data-ebird-details' in line)
    assert ("checked" in checkbox) is expected
    assert ("hidden" not in details) is expected


@pytest.fixture(autouse=True)
def isolated_key_store(tmp_path, monkeypatch):
    monkeypatch.setattr(ebird_locations, 'config_dir', lambda: tmp_path)
    monkeypatch.delenv('EBIRD_API_KEY', raising=False)


def mock_ebird(monkeypatch, status=200):
    import httpx
    tokens = []
    def respond(request):
        tokens.append(request.headers['X-eBirdApiToken'])
        return httpx.Response(status, json=[])
    client = httpx.AsyncClient
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(ebird_locations.httpx, 'AsyncClient',
                        lambda **kwargs: client(transport=transport, **kwargs))
    return tokens


def test_successful_search_saves_key_and_later_search_reuses_it(monkeypatch):
    import os
    import stat
    tokens = mock_ebird(monkeypatch)
    asyncio.run(ebird_locations.nearby_hotspots(42, -71, ' test-key '))
    assert ebird_locations.saved_api_key() == 'test-key'
    # Each call opens a new HTTP client and reads the persisted file.
    monkeypatch.setenv('EBIRD_API_KEY', 'environment-key')
    asyncio.run(ebird_locations.nearby_hotspots(42, -71, ''))
    assert tokens == ['test-key', 'test-key']
    if os.name != 'nt':
        assert stat.S_IMODE(ebird_locations._api_key_path().stat().st_mode) == 0o600


def test_rejected_key_does_not_replace_saved_key(monkeypatch):
    import httpx
    ebird_locations.save_api_key('working-key')
    mock_ebird(monkeypatch, status=403)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(ebird_locations.nearby_hotspots(42, -71, 'bad-key'))
    assert ebird_locations.saved_api_key() == 'working-key'


def test_environment_key_is_used_without_copying_to_disk(monkeypatch):
    tokens = mock_ebird(monkeypatch)
    monkeypatch.setenv('EBIRD_API_KEY', 'environment-key')
    asyncio.run(ebird_locations.nearby_hotspots(42, -71, ''))
    assert tokens == ['environment-key']
    assert not ebird_locations._api_key_path().exists()


def test_explicit_key_replaces_saved_key_after_success(monkeypatch):
    ebird_locations.save_api_key('old-key')
    tokens = mock_ebird(monkeypatch)
    asyncio.run(ebird_locations.nearby_hotspots(42, -71, 'replacement-key'))
    assert tokens == ['replacement-key']
    assert ebird_locations.saved_api_key() == 'replacement-key'


def test_status_and_forget_never_return_saved_key(monkeypatch):
    from fastapi.testclient import TestClient
    from nfc_tools.web.server import create_app
    ebird_locations.save_api_key('private-key-value')
    client = TestClient(create_app())
    response = client.get('/api/ebird/key')
    assert response.json() == {'saved': True, 'environment': False}
    assert response.headers['cache-control'] == 'no-store'
    assert 'private-key-value' not in response.text
    assert client.delete('/api/ebird/key').json() == {'saved': False, 'environment': False}
    assert not ebird_locations._api_key_path().exists()
    assert client.delete('/api/ebird/key').status_code == 200


def test_diagnostic_bundle_excludes_saved_key(tmp_path, monkeypatch):
    import io
    import zipfile
    from fastapi.testclient import TestClient
    from nfc_tools.web import routes_diagnostics
    from nfc_tools.web.server import create_app
    ebird_locations.save_api_key('private-key-value')
    config_path = tmp_path / 'config.yaml'
    config_path.write_text('site: {}\n')
    monkeypatch.setattr(routes_diagnostics.config_mod, 'CONFIG_PATH', config_path)
    monkeypatch.setattr(routes_diagnostics, 'logs_dir', lambda: tmp_path)
    monkeypatch.setattr(routes_diagnostics.doctor, 'run_all', lambda: [])
    response = TestClient(create_app()).get('/diagnostics/bundle')
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert 'config.yaml' in archive.namelist()
        assert 'ebird-api-key' not in archive.namelist()
        assert all(b'private-key-value' not in archive.read(name) for name in archive.namelist())
