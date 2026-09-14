"""Weather snapshot from Open-Meteo. One HTTP call, structured result."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import csv
import httpx
import time
from zoneinfo import ZoneInfo

from .logging_setup import get

log = get("weather")

RETRIABLE_WEATHER_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


@dataclass
class WeatherSnapshot:
    temp_f: Optional[float] = None
    wind_mph: Optional[float] = None
    wind_dir: Optional[float] = None
    upper_wind_mph: Optional[float] = None
    upper_wind_dir: Optional[float] = None
    cloud_pct: Optional[float] = None
    available: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def snapshot(lat: float, lon: float, tz: str) -> WeatherSnapshot:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon, "timezone": tz, "forecast_days": 1,
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "hourly": ",".join([
            "temperature_2m", "cloud_cover",
            "wind_speed_10m", "wind_direction_10m",
            "wind_speed_950hPa", "wind_direction_950hPa",
        ]),
    }
    try:
        data = _weather_json(url, params)["hourly"]
        target = datetime.now().strftime("%Y-%m-%dT%H:00")
        idx = data["time"].index(target)
        return WeatherSnapshot(
            temp_f=data["temperature_2m"][idx],
            wind_mph=data["wind_speed_10m"][idx],
            wind_dir=data["wind_direction_10m"][idx],
            upper_wind_mph=data["wind_speed_950hPa"][idx],
            upper_wind_dir=data["wind_direction_950hPa"][idx],
            cloud_pct=data["cloud_cover"][idx],
            available=True,
        )
    except Exception as e:  # noqa: BLE001
        log.warning("weather unavailable: %s", e)
        return WeatherSnapshot()


def _weather_json(url: str, params: dict, *, attempts: int = 3, timeout: float = 8.0) -> dict:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = httpx.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            if status not in RETRIABLE_WEATHER_STATUS_CODES or attempt == attempts - 1:
                raise
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise
        time.sleep(0.5 * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("weather request failed")


ENVIRONMENT_FIELDS = [
    "logged_date",
    "logged_time",
    "hour_date",
    "hour_time",
    "latitude",
    "longitude",
    "timezone",
    "surface_temp_f",
    "surface_wind_mph",
    "surface_wind_dir_deg",
    "wind_950hpa_mph",
    "wind_950hpa_dir_deg",
    "cloud_cover_pct",
    "available",
    "source",
    "notes",
]


def _date_text(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def _time_text(dt: datetime) -> str:
    return dt.strftime("%H-%M-%S")


def environmental_snapshot(lat: float, lon: float, tz: str, when: datetime | None = None, *, historical: bool = False) -> dict:
    """Return one environmental row for an NFC recording start.

    CSV output uses separate plain-text date and time columns for the recording
    start. Open-Meteo still requires an ISO-style hour key internally for lookup.
    """
    when = when or datetime.now()
    logged = datetime.now()
    zone = ZoneInfo(tz)
    recording_dt = (when.astimezone(zone) if when.tzinfo else when.replace(tzinfo=zone)).replace(microsecond=0)
    hour_dt = recording_dt.replace(minute=0, second=0, microsecond=0)
    hour_key = hour_dt.strftime("%Y-%m-%dT%H:00")
    row = {
        "logged_date": _date_text(logged),
        "logged_time": _time_text(logged),
        "hour_date": _date_text(recording_dt),
        "hour_time": _time_text(recording_dt),
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "surface_temp_f": "",
        "surface_wind_mph": "",
        "surface_wind_dir_deg": "",
        "wind_950hpa_mph": "",
        "wind_950hpa_dir_deg": "",
        "cloud_cover_pct": "",
        "available": False,
        "source": "Open-Meteo",
        "notes": "",
    }

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz,
        "forecast_days": 2,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "hourly": ",".join([
            "temperature_2m",
            "cloud_cover",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_speed_950hPa",
            "wind_direction_950hPa",
        ]),
    }

    if historical:
        # Historical Forecast includes upper-air fields; the older reanalysis
        # archive has surface fields only. Never substitute present-day weather.
        day = recording_dt.date()
        old_archive = day.year < 2022
        url = ("https://archive-api.open-meteo.com/v1/archive" if old_archive else
               "https://historical-forecast-api.open-meteo.com/v1/forecast")
        if day >= datetime.now(zone).date() - timedelta(days=2):
            url = "https://api.open-meteo.com/v1/forecast"
        params.pop("forecast_days")
        utc_day = recording_dt.astimezone(timezone.utc).date().isoformat()
        params.update(start_date=utc_day, end_date=utc_day, timezone="UTC", timeformat="unixtime")
        if old_archive:
            params["hourly"] = ",".join(key for key in params["hourly"].split(",") if "950hPa" not in key)
            row["notes"] = "950 hPa wind unavailable in the historical surface archive."
        row["source"] = url

    try:
        data = _weather_json(url, params)["hourly"]
        if historical:
            # Match by instant, including the second occurrence of a DST hour.
            timestamp = recording_dt.timestamp()
            idx = max(i for i, value in enumerate(data["time"]) if value <= timestamp)
            if timestamp - data["time"][idx] >= 3600:
                raise ValueError("Weather data does not cover the recording hour")
        else:
            idx = data["time"].index(hour_key)
        row.update({
            "surface_temp_f": data["temperature_2m"][idx],
            "surface_wind_mph": data["wind_speed_10m"][idx],
            "surface_wind_dir_deg": data["wind_direction_10m"][idx],
            "wind_950hpa_mph": data.get("wind_speed_950hPa", [None] * len(data["time"]))[idx],
            "wind_950hpa_dir_deg": data.get("wind_direction_950hPa", [None] * len(data["time"]))[idx],
            "cloud_cover_pct": data["cloud_cover"][idx],
            "available": True,
        })
    except Exception as e:  # noqa: BLE001
        row["notes"] = f"Weather unavailable: {e}"
        log.warning("environmental conditions unavailable: %s", e)

    return row


def append_environment_csv(night_path: Path, row: dict) -> Path:
    path = night_path / "logs" / "environmental_conditions.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists() or path.stat().st_size == 0
    normalized = {field: row.get(field, "") for field in ENVIRONMENT_FIELDS}
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ENVIRONMENT_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(normalized)
    return path


def _condition_value(value, suffix: str = "") -> str:
    if value in ("", None):
        return "unavailable"
    return f"{value}{suffix}"


def environment_text_line(row: dict) -> str:
    return " | ".join([
        f"Date: {_condition_value(row.get('hour_date'))}",
        f"Time: {_condition_value(row.get('hour_time'))}",
        environment_conditions_text_line(row),
    ])


def environment_conditions_text_line(row: dict) -> str:
    degree = "\N{DEGREE SIGN}"
    return " | ".join([
        f"Temperature (F): {_condition_value(row.get('surface_temp_f'), degree)}",
        f"Wind speed: {_condition_value(row.get('surface_wind_mph'), ' mph')}",
        f"Wind direction: {_condition_value(row.get('surface_wind_dir_deg'), degree)}",
        f"950 hPa wind speed: {_condition_value(row.get('wind_950hpa_mph'), ' mph')}",
        f"950 hPa wind direction: {_condition_value(row.get('wind_950hpa_dir_deg'), degree)}",
        f"Cloud cover: {_condition_value(row.get('cloud_cover_pct'), '%')}",
    ])


def append_environment_text(night_path: Path, row: dict) -> Path:
    path = night_path / "logs" / "environmental_conditions.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(environment_text_line(row) + "\n")
    return path
