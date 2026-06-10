"""Weather snapshot from Open-Meteo. One HTTP call, structured result."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
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
