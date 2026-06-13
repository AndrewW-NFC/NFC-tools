"""Weather snapshot from Open-Meteo. One HTTP call, structured result."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
import csv
import httpx

from .logging_setup import get

log = get("weather")


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
        r = httpx.get(url, params=params, timeout=8.0)
        r.raise_for_status()
        data = r.json()["hourly"]
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


ENVIRONMENT_FIELDS = [
    "logged_at",
    "hour_local",
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


def environmental_snapshot(lat: float, lon: float, tz: str, when: datetime | None = None) -> dict:
    """Return one hourly environmental row for NFC review.

    This mirrors the older AppleScript weather log: surface temperature,
    surface wind speed/direction, 950 hPa wind speed/direction, and cloud cover
    from Open-Meteo for the local hour being recorded.
    """
    when = when or datetime.now()
    hour_local = when.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:00")
    row = {
        "logged_at": datetime.now().isoformat(timespec="seconds"),
        "hour_local": hour_local,
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

    try:
        r = httpx.get(url, params=params, timeout=8.0)
        r.raise_for_status()
        data = r.json()["hourly"]
        idx = data["time"].index(hour_local)
        row.update({
            "surface_temp_f": data["temperature_2m"][idx],
            "surface_wind_mph": data["wind_speed_10m"][idx],
            "surface_wind_dir_deg": data["wind_direction_10m"][idx],
            "wind_950hpa_mph": data["wind_speed_950hPa"][idx],
            "wind_950hpa_dir_deg": data["wind_direction_950hPa"][idx],
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
