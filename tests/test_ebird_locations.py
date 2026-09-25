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
