import csv
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from nfc_tools.acoustics import MODEL_VERSION, descriptor, score_weather
from nfc_tools.ebird_export import EbirdExportOptions, _submission_comments
from nfc_tools.weather import append_environment_csv, environmental_snapshot


def ideal():
    return {
        "surface_temp_f": 50,
        "surface_wind_mph": 0,
        "surface_gust_mph": 0,
        "relative_humidity_pct": 72,
        "precipitation_mm": 0,
        "cloud_cover_pct": 50,
        "surface_pressure_hpa": 1025,
        "visibility_m": 10000,
    }


def test_unknown_site_factors_are_neutral():
    result = score_weather(ideal())
    assert (
        result["acoustic_score"] == 9.25
    )  # Full model's 10 minus 0.4 + 0.35 site bonuses.
    assert result["acoustic_descriptor"] == "Excellent"
    assert result["acoustic_model_version"] == MODEL_VERSION


@pytest.mark.parametrize(
    "value,label",
    [(6.74, "Fair"), (6.75, "Good"), (7.75, "Very Good"), (8.75, "Excellent")],
)
def test_descriptor_rounds_half_up_like_javascript(value, label):
    assert descriptor(value) == label


@pytest.mark.parametrize("value", ["", None, float("nan"), float("inf"), -1])
def test_unknown_or_invalid_humidity_does_not_receive_bonus(value):
    assert (
        score_weather({**ideal(), "relative_humidity_pct": value})[
            "acoustic_descriptor"
        ]
        == "unavailable"
    )


def test_visibility_fallback_matches_upstream():
    assert score_weather({**ideal(), "visibility_m": ""}) == score_weather(ideal())


@pytest.mark.parametrize("historical", [False, True])
def test_snapshot_saves_score_and_exports_comment(monkeypatch, tmp_path, historical):
    from nfc_tools import weather

    when = datetime(2024, 8, 8, 23, 30, tzinfo=ZoneInfo("UTC"))

    def fetch(url, params):
        assert "relative_humidity_2m" in params["hourly"]
        assert params["precipitation_unit"] == "mm"
        return {
            "hourly": {
                "time": [int(when.replace(minute=0).timestamp())]
                if historical
                else ["2024-08-08T23:00"],
                "temperature_2m": [50],
                "wind_speed_10m": [0],
                "wind_direction_10m": [0],
                "cloud_cover": [50],
                "relative_humidity_2m": [72],
                "precipitation": [0],
                "wind_gusts_10m": [0],
                "surface_pressure": [1025],
                "visibility": [10000],
            }
        }

    # Use UTC timestamps explicitly, independent of the test machine's timezone.
    monkeypatch.setattr(weather, "_weather_json", fetch)
    row = environmental_snapshot(42, -71, "UTC", when, historical=historical)
    assert row["acoustic_descriptor"] == "Excellent"
    append_environment_csv(tmp_path, row)
    comment = _submission_comments(
        tmp_path,
        "001_NFC_2024-08-08_23-30-00.wav",
        EbirdExportOptions(
            location_name="Test", latitude=42, longitude=-71, state_province="MA"
        ),
    )
    assert (
        "Acoustic conditions: Excellent (weather-only estimate; foliage and insect noise not assessed)"
        in comment
    )
    assert "https://github.com/AndrewW-NFC/nfc-acoustic-environment-forecast" in comment


def test_old_log_schema_upgraded_without_losing_rows(tmp_path):
    path = tmp_path / "logs" / "environmental_conditions.csv"
    path.parent.mkdir()
    path.write_text("hour_date,hour_time,available\n2024-08-08,22-00-00,True\n")
    append_environment_csv(
        tmp_path,
        {"hour_date": "2024-08-08", "hour_time": "23-00-00", **score_weather(ideal())},
    )
    with path.open() as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["hour_time"] == "22-00-00"
    assert rows[0]["acoustic_descriptor"] == ""
    assert rows[1]["acoustic_descriptor"] == "Excellent"


def test_no_log_exports_unavailable(tmp_path):
    assert "Acoustic conditions: unavailable" in _submission_comments(
        tmp_path,
        "001_NFC_2024-08-08_23-00-00.wav",
        EbirdExportOptions(
            location_name="Test", latitude=42, longitude=-71, state_province="MA"
        ),
    )
