import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from nfc_tools import precipitation as rain

CASES = json.loads(Path(__file__).with_name("precipitation-fixtures.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_shared_contract(case):
    result = rain.summarize_payload(case["data"], case["evening"], 42.41465, -71.17286,
                                    case["timezone"], now=datetime.fromtimestamp(case["now"], timezone.utc))
    assert result["total_mm"] == case["total"]
    assert result["status"] == case["status"]
    assert result["expected_hours"] == case["hours"]
    assert len({i["interval_end_utc"] for i in result["intervals"]}) == case["hours"]


def test_fetch_pins_source_and_utc_intervals(monkeypatch):
    calls = []
    monkeypatch.setattr(rain, "_weather_json", lambda url, params: calls.append((url, params)) or CASES[0]["data"])
    rain.fetch_summary("2026-03-07", 42, -71, "America/New_York")
    url, params = calls[0]
    assert url == rain.SOURCE
    assert params["models"] == "ecmwf_ifs"
    assert params["timezone"] == "UTC"
    assert params["timeformat"] == "unixtime"
    assert params["precipitation_unit"] == "mm"
    assert params["start_date"] == "2026-03-07"
    assert params["end_date"] == "2026-03-08"


def test_refresh_preserves_snapshot_log_and_uses_saved_site(tmp_path, monkeypatch):
    nd = tmp_path / "2026-09-20"
    logs = nd / "logs"
    logs.mkdir(parents=True)
    original = "latitude,longitude,timezone\n42,-71,America/New_York\n42,-71,America/New_York\n"
    (logs / "environmental_conditions.csv").write_text(original)
    calls = []
    monkeypatch.setattr(rain, "fetch_summary", lambda *args: calls.append(args) or {"status": "complete", "total_mm": 1})
    rain.refresh_night(nd)
    assert calls == [("2026-09-20", 42, -71, "America/New_York")]
    assert (logs / "environmental_conditions.csv").read_text() == original
    assert rain.saved_summary(nd)["total_mm"] == 1
    monkeypatch.setattr(rain, "fetch_summary", lambda *args: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(RuntimeError):
        rain.refresh_night(nd)
    assert rain.saved_summary(nd)["total_mm"] == 1


def test_mixed_sites_are_not_silently_merged(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs/environmental_conditions.csv").write_text("latitude,longitude,timezone\n42,-71,UTC\n43,-71,UTC\n")
    with pytest.raises(ValueError, match="exactly one"):
        rain.refresh_night(tmp_path)


def test_web_refresh_returns_report_and_retains_http_failure(monkeypatch, tmp_path):
    from fastapi import HTTPException
    from nfc_tools.web import routes_nights
    monkeypatch.setattr(routes_nights, "night_path", lambda _: tmp_path)
    monkeypatch.setattr(rain, "refresh_night", lambda _: {"status": "complete", "total_mm": 1.4})
    assert routes_nights.refresh_precipitation("2026-09-20")["total_mm"] == 1.4
    monkeypatch.setattr(rain, "refresh_night", lambda _: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(HTTPException) as error:
        routes_nights.refresh_precipitation("2026-09-20")
    assert error.value.status_code == 502
    assert "previous report retained" in error.value.detail
