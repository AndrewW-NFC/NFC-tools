from datetime import datetime

import nfc_tools.weather as weather_mod
from nfc_tools.weather import append_environment_text, environment_text_line, environmental_snapshot


def test_environment_text_line_is_paste_ready_with_timestamp():
    row = {
        "hour_date": "2026-06-18",
        "hour_time": "02-00-00",
        "surface_temp_f": 63.4,
        "surface_wind_mph": 4.8,
        "surface_wind_dir_deg": 210,
        "wind_950hpa_mph": 11.2,
        "wind_950hpa_dir_deg": 235,
        "cloud_cover_pct": 18,
        "source": "Open-Meteo",
        "notes": "not included",
    }

    assert environment_text_line(row) == (
        "Date: 2026-06-18 | Time: 02-00-00 | "
        "Temperature (F): 63.4° | Wind speed: 4.8 mph | Wind direction: 210° | "
        "950 hPa wind speed: 11.2 mph | 950 hPa wind direction: 235° | Cloud cover: 18%"
    )


def test_append_environment_text_writes_one_line_per_snapshot(tmp_path):
    row = {
        "surface_temp_f": "",
        "surface_wind_mph": None,
        "surface_wind_dir_deg": "",
        "wind_950hpa_mph": "",
        "wind_950hpa_dir_deg": "",
        "cloud_cover_pct": "",
    }

    path = append_environment_text(tmp_path, row)

    assert path == tmp_path / "logs" / "environmental_conditions.txt"
    assert path.read_text(encoding="utf-8") == (
        "Date: unavailable | Time: unavailable | "
        "Temperature (F): unavailable | Wind speed: unavailable | Wind direction: unavailable | "
        "950 hPa wind speed: unavailable | 950 hPa wind direction: unavailable | Cloud cover: unavailable\n"
    )


def test_environmental_snapshot_keeps_recording_start_time_with_hourly_weather(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2026-06-18T22:00"],
                    "temperature_2m": [63.4],
                    "cloud_cover": [18],
                    "wind_speed_10m": [4.8],
                    "wind_direction_10m": [210],
                    "wind_speed_950hPa": [11.2],
                    "wind_direction_950hPa": [235],
                }
            }

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return Response()

    monkeypatch.setattr(weather_mod.httpx, "get", fake_get)

    row = environmental_snapshot(
        42.0,
        -71.0,
        "America/New_York",
        datetime(2026, 6, 18, 22, 58, 17, 123456),
    )

    assert calls
    assert row["hour_date"] == "2026-06-18"
    assert row["hour_time"] == "22-58-17"
    assert row["surface_temp_f"] == 63.4
    assert row["available"] is True


def test_environmental_snapshot_keeps_midnight_recording_start_time(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hourly": {
                    "time": ["2026-06-19T00:00"],
                    "temperature_2m": [58.1],
                    "cloud_cover": [40],
                    "wind_speed_10m": [6.0],
                    "wind_direction_10m": [180],
                    "wind_speed_950hPa": [15.0],
                    "wind_direction_950hPa": [220],
                }
            }

    monkeypatch.setattr(weather_mod.httpx, "get", lambda *args, **kwargs: Response())

    row = environmental_snapshot(42.0, -71.0, "America/New_York", datetime(2026, 6, 19, 0, 0, 0))

    assert row["hour_date"] == "2026-06-19"
    assert row["hour_time"] == "00-00-00"
    assert row["available"] is True
