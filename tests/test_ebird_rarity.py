import csv
from datetime import date

import pytest

from nfc_tools.config import Config
from nfc_tools.ebird_export import Detection, Taxon, options_for_site, prepare_record_export
from nfc_tools.ebird_rarity import RARITY_COMMENT, annotate, filter_for_site, parse_filter, site_association

SAMPLE = b"American Redstart,Jan 1,0,Sep 1,20,Oct 1,0\nSwainson's Thrush,Jan 1,0\n"


def configured():
    cfg = Config()
    cfg.site.ebird_state_province = 'MA'
    cfg.site.ebird_rarity_filter = parse_filter(SAMPLE, 'reviewer.csv', 'Test county')
    cfg.site.ebird_rarity_filter.association = site_association(cfg.site)
    cfg.site.ebird_rarity_enabled = True
    return cfg


@pytest.mark.parametrize('day, expected', [('2026-08-31', 'rare'), ('2026-09-01', 'not flagged'),
    ('2026-09-30', 'not flagged'), ('2026-10-01', 'rare'), ('2026-12-31', 'rare'),
    ('2027-01-01', 'rare'), ('2028-02-29', 'rare')])
def test_annual_boundaries(day, expected):
    profile = configured().site.ebird_rarity_filter
    assert profile.evaluate('American Redstart', date.fromisoformat(day))[0] == expected
    assert profile.evaluate('Absent species', date.fromisoformat(day)) == ('not evaluated', '')


@pytest.mark.parametrize('content', [b'', b'Name,Jan 1', b'Name,Jan 1,-1', b'Name,Jan 1,no',
    b'Name,Apr 31,0', b'Name,Jan 1,0,Jan 1,1', b'Name,Feb 1,0', b'Name,Jan 1,0\nName,Jan 1,1',
    b'Name,Jan 1,0,Dec 1,1,Nov 1,0', b'\xff', b'Name,Jan 1,0,Feb 29,2'])
def test_invalid_filters(content):
    with pytest.raises(ValueError):
        parse_filter(content, 'file.csv', 'County')


def test_comment_preservation_and_exact_matching():
    profile = configured().site.ebird_rarity_filter
    today = date(2026, 10, 1)
    comment = annotate('NFC 3 | BirdNET detections 2', profile, 'American Redstart', today)
    assert comment == 'NFC 3 | BirdNET detections 2 | ' + RARITY_COMMENT
    assert annotate(comment, profile, 'American Redstart', today) == comment
    assert annotate('NFC 1', profile, 'thrush sp.', today) == 'NFC 1'
    assert annotate('NFC 1', None, 'American Redstart', today) == 'NFC 1'


def test_filter_survives_configuration_snapshot_and_requires_location_coverage():
    cfg = Config.model_validate(configured().model_dump())
    assert filter_for_site(cfg.site).region == 'Test county'
    cfg.site.latitude += 1
    with pytest.raises(ValueError, match='coverage'):
        filter_for_site(cfg.site)
    cfg.site.ebird_rarity_enabled = False
    assert filter_for_site(cfg.site) is None


def test_each_recording_uses_its_own_calendar_date(tmp_path, monkeypatch):
    from nfc_tools import ebird_export
    recordings = ['001_NFC_2026-09-30_23-35-00.wav', '002_NFC_2026-10-01_00-00-00.wav']
    detections = [Detection(name, 'Nighthawk', 'amered', 0, 1, .9, Taxon('American Redstart'))
                  for name in recordings]
    detections.append(Detection(recordings[1], 'BirdNET', 'unknown', 0, 1, .9, Taxon('Unknown bird')))
    monkeypatch.setattr(ebird_export, '_night_detections', lambda _: detections)
    night = tmp_path / '2026-09-30'
    result = prepare_record_export(night, options_for_site(configured().site))
    rows = list(csv.reader(result['combined_import_path'].open()))
    redstarts = [row for row in rows if row[0] == 'American Redstart']
    assert [row[8] for row in redstarts] == ['9/30/2026', '10/1/2026']
    assert redstarts[0][4] == 'NFC 1'
    assert redstarts[1][4] == 'NFC 1 | ' + RARITY_COMMENT
    review = list(csv.DictReader(result['combined_review_path'].open(encoding='utf-8-sig')))
    assert [row['ebird_rarity_status'] for row in review if row['common_name'] == 'American Redstart'] == ['not flagged', 'rare']
    unknown = next(row for row in review if row['common_name'] == 'Unknown bird')
    assert unknown['ebird_rarity_status'] == 'not evaluated'
    assert unknown['ebird_rarity_region'] == 'Test county'
    # Regeneration is idempotent; enabled filters don't alter uploads' field layout.
    again = prepare_record_export(night, options_for_site(configured().site))
    assert list(csv.reader(again['combined_import_path'].open())) == rows
    assert all(len(row) == 19 for row in rows)


@pytest.fixture
def settings_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from nfc_tools.web import routes
    from nfc_tools.web.server import create_app
    monkeypatch.setattr(routes.state, 'cfg', Config())
    monkeypatch.setattr(routes.config_mod, 'CONFIG_PATH', tmp_path / 'config.yaml')
    monkeypatch.setattr(routes, '_timezone_for_site', lambda *args: 'America/New_York')
    return TestClient(create_app()), routes


def test_upload_save_reload_preview_and_failed_replacement(settings_client):
    client, routes = settings_client
    form = dict(ebird_rarity_present='1', ebird_rarity_enabled='on', ebird_rarity_confirm='on',
                ebird_rarity_region='Test county', ebird_state_province='MA')
    response = client.post('/settings/save', data=form, files={'ebird_rarity_csv': ('filter.csv', SAMPLE, 'text/csv')}, follow_redirects=False)
    assert response.status_code == 303, response.text
    cfg = routes.config_mod.load()
    assert filter_for_site(cfg.site).source == 'filter.csv'
    assert cfg.site.ebird_rarity_filter.preview()
    html = routes.templates.env.get_template('ebird_location.html').render(
        location_prefix="", cfg=cfg.model_dump(), rarity_preview=cfg.site.ebird_rarity_filter.preview(), devices=[],
        schedule_presets=[], schedule_preview={}, install_status={})
    assert 'Test county' in html and '09-01' not in str(cfg.site.ebird_rarity_filter.preview())
    before = routes.state.cfg.model_dump()
    response = client.post('/settings/save', data=form, files={'ebird_rarity_csv': ('bad.csv', b'bad', 'text/csv')})
    assert response.status_code == 400
    assert routes.state.cfg.model_dump() == before
    assert routes.config_mod.load().model_dump() == before
    form.pop('ebird_rarity_confirm')
    form['latitude'] = 10
    assert client.post('/settings/save', data=form).status_code == 400
    assert routes.state.cfg.model_dump() == before


def test_disabled_exports_keep_review_csv_unchanged(tmp_path, monkeypatch):
    from nfc_tools import ebird_export
    cfg = configured()
    cfg.site.ebird_export_enabled = False
    assert options_for_site(cfg.site).rarity_filter is None
    assert 'ebird_rarity_status' not in ebird_export.REVIEW_FIELDS


def test_bom_crlf_and_positive_thresholds():
    profile = parse_filter(b'\xef\xbb\xbf"Test bird",Jan 1,200,Mar 1,0\r\n', 'a.csv', 'County')
    assert profile.evaluate('Test bird', date(2026, 2, 28))[0] == 'not flagged'
    assert profile.evaluate('Test bird', date(2026, 3, 1))[0] == 'rare'


def test_coordinate_change_disables_filter_until_reconfirmed(settings_client):
    client, routes = settings_client
    routes.state.cfg = configured()
    response = client.post('/settings/site-coordinates', data={'latitude': '41', 'longitude': '-72'})
    assert response.status_code == 200
    assert response.json()['rarity_enabled'] is False
    assert routes.state.cfg.site.ebird_rarity_filter is not None
    assert not routes.config_mod.load().site.ebird_rarity_enabled


def test_diagnostic_bundle_omits_private_thresholds(settings_client, tmp_path, monkeypatch):
    import io
    import zipfile
    import yaml
    from nfc_tools.web import routes_diagnostics
    client, routes = settings_client
    cfg = configured()
    routes.config_mod.save(cfg)
    monkeypatch.setattr(routes_diagnostics, 'logs_dir', lambda: tmp_path)
    monkeypatch.setattr(routes_diagnostics.doctor, 'run_all', lambda: [])
    response = client.get('/diagnostics/bundle')
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        data = yaml.safe_load(archive.read('config.yaml'))
        assert 'ebird_rarity_filter' not in data['site']
        assert not data['site']['ebird_rarity_enabled']
    assert routes.config_mod.load().site.ebird_rarity_filter is not None


def test_new_filter_requires_explicit_coverage(settings_client):
    client, routes = settings_client
    before = routes.state.cfg.model_dump()
    response = client.post('/settings/save', data={'ebird_rarity_present': '1', 'ebird_rarity_enabled': 'on',
                           'ebird_rarity_region': 'Test county'}, files={'ebird_rarity_csv': ('test.csv', SAMPLE)})
    assert response.status_code == 400
    assert routes.state.cfg.model_dump() == before
