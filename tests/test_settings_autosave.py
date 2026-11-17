"""Settings autosave persists only the edited section and reports failed writes."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from nfc_tools.config import Config
from nfc_tools.web import routes
from nfc_tools.web.server import create_app


@pytest.fixture
def setup(tmp_path, monkeypatch):
    cfg = Config()
    cfg.recording.device = 'name:MacBook Air Microphone'
    cfg.power.analyze_with_lid_closed = True
    cfg.analyzers.birdnet_owl_sensitivity = True
    monkeypatch.setattr(routes.state, 'cfg', cfg)
    monkeypatch.setattr(routes.config_mod, 'CONFIG_PATH', tmp_path / 'config.yaml')
    monkeypatch.setattr(routes, '_timezone_for_site', lambda *args: 'America/New_York')
    monkeypatch.setattr(routes, 'list_input_devices', lambda: [
        {'id': 'avfoundation:0', 'name': 'External Microphone'},
        {'id': 'avfoundation:1', 'name': 'MacBook Air Microphone'},
    ])
    monkeypatch.setattr(routes, 'current_schedule_preview', lambda cfg: SimpleNamespace(
        start_time='18:00', end_time='06:00'))
    return TestClient(create_app()), cfg


def test_microphone_autosave_persists_without_touching_unfinished_ebird_or_other_options(setup):
    client, cfg = setup
    before = cfg.model_dump()
    response = client.post('/settings/save', data={
        '_section': 'microphone', 'device_id': 'name:External Microphone',
        'latitude': 'invalid', 'ebird_options_present': '1', 'ebird_export_enabled': 'on',
    })
    assert response.status_code == 200
    assert 'External Microphone' in response.json()['device_status']
    before['recording']['device'] = 'name:External Microphone'
    assert cfg.model_dump() == before
    assert routes.config_mod.load().recording.device == 'name:External Microphone'


@pytest.mark.parametrize('section, fields, path, expected', [
    ('site', {'site_name': 'New site', 'latitude': '41.2', 'longitude': '-70'}, ('site', 'name'), 'New site'),
    ('storage', {'save_location': ''}, ('recording', 'save_location'), ''),
    ('format', {'format_preset': 's16_441', 'recording_backend': 'ffmpeg'}, ('recording', 'sample_rate'), 44100),
    ('schedule', {'schedule_mode': 'manual', 'start_time': '20:00', 'end_time': '05:00'}, ('schedule', 'start_time'), '20:00'),
    ('power', {'analysis_policy': 'defer_on_battery'}, ('power', 'analyze_with_lid_closed'), False),
    ('analyzers', {}, ('analyzers', 'enabled'), []),
    ('ebird', {'ebird_options_present': '1'}, ('site', 'ebird_export_enabled'), False),
])
def test_each_section_persists_and_can_clear_checkboxes(setup, section, fields, path, expected):
    client, cfg = setup
    response = client.post('/settings/save', data={'_section': section, **fields})
    assert response.status_code == 200, response.text
    loaded = routes.config_mod.load()
    assert getattr(getattr(loaded, path[0]), path[1]) == expected
    assert cfg.recording.device == 'name:MacBook Air Microphone'


@pytest.mark.parametrize('section, fields', [
    ('site', {'latitude': ''}), ('site', {'latitude': 'nan'}), ('site', {'longitude': '181'}),
    ('power', {'critical_battery_percent': '101'}), ('schedule', {'start_time': '25:00', 'schedule_mode': 'manual'}),
    ('schedule', {'segment_minutes': '0'}), ('analyzers', {'birdnet_min_conf': 'nan'}),
    ('format', {'format_preset': 'unknown'}), ('unknown', {}),
])
def test_invalid_values_do_not_commit(setup, section, fields):
    client, cfg = setup
    before = cfg.model_dump()
    response = client.post('/settings/save', data={'_section': section, **fields})
    assert response.status_code == 400
    assert cfg.model_dump() == before
    assert not routes.config_mod.CONFIG_PATH.exists()


def test_disk_failure_is_reported_and_does_not_update_shared_configuration(setup, monkeypatch):
    client, cfg = setup
    def fail(_):
        raise OSError('disk full')
    monkeypatch.setattr(routes.config_mod, 'save', fail)
    response = client.post('/settings/save', data={'_section': 'microphone', 'device_id': 'name:External Microphone'})
    assert response.status_code == 500
    assert 'not been saved' in response.json()['error']
    assert cfg.recording.device == 'name:MacBook Air Microphone'


def test_rarity_upload_requires_confirmation_and_location_change_disables_it(setup):
    client, cfg = setup
    data = {'_section': 'ebird', 'ebird_rarity_present': '1', 'ebird_rarity_enabled': 'on',
            'ebird_rarity_region': 'Test county'}
    files = {'ebird_rarity_csv': ('reviewer.csv', b"American Redstart,Jan 1,0\n", 'text/csv')}
    response = client.post('/settings/save', data=data, files=files)
    assert response.status_code == 400
    assert cfg.site.ebird_rarity_filter is None
    response = client.post('/settings/save', data={**data, 'ebird_rarity_confirm': 'on'}, files=files)
    assert response.status_code == 200
    assert routes.config_mod.load().site.ebird_rarity_enabled
    response = client.post('/settings/save', data={'_section': 'site', 'latitude': '40'})
    assert response.status_code == 200
    assert not response.json()['rarity_enabled']
    assert not routes.config_mod.load().site.ebird_rarity_enabled
