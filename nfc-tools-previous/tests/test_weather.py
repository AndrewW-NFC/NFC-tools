from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

import nfc_tools.weather as weather_mod
from nfc_tools.weather import (
    _weather_json,
    append_environment_text,
    environment_text_line,
    environmental_snapshot,
)


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
        "precipitation_mm": 1.2,
        "source": "Open-Meteo",
        "notes": "not included",
    }

    assert environment_text_line(row) == (
        "Date: 2026-06-18 | Time: 02-00-00 | "
        "Temperature (F): 63.4° | Wind speed: 4.8 mph | Wind direction: 210° | "
        "950 hPa wind speed: 11.2 mph | 950 hPa wind direction: 235° | Cloud cover: 18% | Precipitation: 1.2 mm"
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
        "950 hPa wind speed: unavailable | 950 hPa wind direction: unavailable | Cloud cover: unavailable | Precipitation: unavailable\n"
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


def test_weather_json_retries_transient_timeouts(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"hourly": {"time": []}}

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow weather response")
        return Response()

    monkeypatch.setattr(weather_mod.httpx, "get", fake_get)
    monkeypatch.setattr(weather_mod.time, "sleep", lambda _seconds: None)

    assert _weather_json("https://example.test/weather", {"latitude": 42}) == {"hourly": {"time": []}}
    assert len(calls) == 2


def test_historical_weather_uses_corrected_instant_and_utc_request_date(monkeypatch):
    calls = []
    when = datetime(2024, 8, 8, 23, 30, tzinfo=ZoneInfo('America/New_York'))
    hour = int(when.replace(minute=0).timestamp())
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {'hourly': {'time': [hour], 'temperature_2m': [60], 'cloud_cover': [15],
                               'wind_speed_10m': [5], 'wind_direction_10m': [100],
                               'wind_speed_950hPa': [20], 'wind_direction_950hPa': [180]}}
    def get(url, params, timeout):
        calls.append((url, params))
        return Response()
    monkeypatch.setattr(weather_mod.httpx, 'get', get)
    row = environmental_snapshot(42, -71, 'America/New_York', when, historical=True)
    assert row['available'] is True
    assert row['hour_date'] == '2024-08-08'
    assert row['hour_time'] == '23-30-00'
    assert row['wind_950hpa_mph'] == 20
    url, params = calls[0]
    assert 'historical-forecast-api' in url
    assert params['start_date'] == params['end_date'] == '2024-08-09'
    assert params['timezone'] == 'UTC'


def test_historical_weather_failure_is_reported_not_substituted(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('offline')
    monkeypatch.setattr(weather_mod.httpx, 'get', fail)
    row = environmental_snapshot(42, -71, 'America/New_York', datetime(2024, 8, 9, 3, 30), historical=True)
    assert row['available'] is False
    assert row['hour_date'] == '2024-08-09'
    assert row['surface_temp_f'] == ''
    assert 'offline' in row['notes']


def test_cached_forecast_uses_requested_hour_and_preserves_retrieval_time(monkeypatch):
    monkeypatch.setattr(weather_mod, '_FORECAST_CACHE', weather_mod.OrderedDict())
    data = {'hourly': {'time': ['2026-06-18T23:00', '2026-06-19T00:00'],
                      'temperature_2m': [60, 55], 'cloud_cover': [10, 20],
                      'wind_speed_10m': [2, 3], 'wind_direction_10m': [90, 100]}}
    monkeypatch.setattr(weather_mod, '_weather_json', lambda *args: data)
    first = environmental_snapshot(42, -71, 'UTC', datetime(2026, 6, 18, 23, tzinfo=ZoneInfo("UTC")))

    def offline(*args):
        raise httpx.ConnectError('offline')
    monkeypatch.setattr(weather_mod, '_weather_json', offline)
    row = environmental_snapshot(42, -71, 'UTC', datetime(2026, 6, 19, 0, 15, tzinfo=ZoneInfo("UTC")))
    assert row['available']
    assert row['surface_temp_f'] == 55
    assert row['hour_time'] == '00-15-00'
    assert row['weather_retrieved_at_utc'] == first['weather_retrieved_at_utc']
    assert 'cached forecast' in row['notes']
    assert 'Cached forecast retrieved' in environment_text_line(row)
    # Neither another site nor an uncovered hour can borrow these conditions.
    assert not environmental_snapshot(43, -71, 'UTC', datetime(2026, 6, 19, tzinfo=ZoneInfo("UTC")))['available']
    assert not environmental_snapshot(42, -71, 'UTC', datetime(2026, 6, 19, 1, tzinfo=ZoneInfo("UTC")))['available']
    assert not environmental_snapshot(42, -71, 'UTC', datetime(2026, 6, 19, tzinfo=ZoneInfo("UTC")), historical=True)['available']
    monkeypatch.setattr(weather_mod.time, 'monotonic', lambda: 10**15)
    assert not environmental_snapshot(42, -71, 'UTC', datetime(2026, 6, 19, tzinfo=ZoneInfo("UTC")))['available']


def test_bad_forecast_does_not_replace_cached_data(monkeypatch):
    monkeypatch.setattr(weather_mod, '_FORECAST_CACHE', weather_mod.OrderedDict())
    data = {'hourly': {'time': ['2026-06-18T23:00'], 'temperature_2m': [60],
                      'cloud_cover': [10], 'wind_speed_10m': [2], 'wind_direction_10m': [90]}}
    monkeypatch.setattr(weather_mod, '_weather_json', lambda *args: data)
    when = datetime(2026, 6, 18, 23, tzinfo=ZoneInfo("UTC"))
    assert environmental_snapshot(42, -71, 'UTC', when)['available']
    monkeypatch.setattr(weather_mod, '_weather_json', lambda *args: {'hourly': {}})
    row = environmental_snapshot(42, -71, 'UTC', when)
    assert row['available']
    assert row['surface_temp_f'] == 60
    assert 'cached forecast' in row['notes']


def test_weather_json_retries_invalid_json(monkeypatch):
    responses = iter([httpx.Response(200, text='<html>temporary error</html>',
                                     request=httpx.Request('GET', 'https://example.test')),
                      httpx.Response(200, json={'hourly': {}},
                                     request=httpx.Request('GET', 'https://example.test'))])
    monkeypatch.setattr(weather_mod.httpx, 'get', lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(weather_mod.time, 'sleep', lambda seconds: None)
    assert _weather_json('https://example.test', {}) == {'hourly': {}}
