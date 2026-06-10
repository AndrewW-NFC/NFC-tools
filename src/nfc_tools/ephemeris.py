"""Sunset / sunrise computation using NOAA's algorithm.

We avoid heavy astronomy libraries; this is good to ~1 minute, which
is plenty for "30 minutes after sunset" scheduling. Returned times
are local clock times for the given timezone.
"""
from __future__ import annotations
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dataclasses import dataclass


@dataclass
class SunTimes:
	sunrise: datetime  # local
	sunset: datetime   # local


def _solar_event(d: date, lat: float, lon: float, rising: bool) -> datetime | None:
	"""Return UTC datetime of sunrise (rising=True) or sunset on date d."""
	n = d.timetuple().tm_yday
	lng_hour = lon / 15.0
	t = n + ((6 - lng_hour) / 24 if rising else (18 - lng_hour) / 24)
	M = (0.9856 * t) - 3.289
	L = (M + (1.916 * math.sin(math.radians(M)))
		   + (0.020 * math.sin(math.radians(2 * M))) + 282.634) % 360
	RA = math.degrees(math.atan(0.91764 * math.tan(math.radians(L)))) % 360
	Lq = (math.floor(L / 90)) * 90
	RAq = (math.floor(RA / 90)) * 90
	RA = (RA + (Lq - RAq)) / 15
	sinDec = 0.39782 * math.sin(math.radians(L))
	cosDec = math.cos(math.asin(sinDec))
	zenith = 90.833
	cosH = ((math.cos(math.radians(zenith)) - (sinDec * math.sin(math.radians(lat))))
			/ (cosDec * math.cos(math.radians(lat))))
	if cosH > 1 or cosH < -1:
		return None
	H = (360 - math.degrees(math.acos(cosH))) if rising else math.degrees(math.acos(cosH))
	H = H / 15
	T = H + RA - (0.06571 * t) - 6.622
	UT = (T - lng_hour) % 24
	hours = int(UT)
	minutes = int((UT - hours) * 60)
	seconds = int((((UT - hours) * 60) - minutes) * 60)
	return datetime(d.year, d.month, d.day, hours, minutes, seconds, tzinfo=timezone.utc)


def sun_times(d: date, lat: float, lon: float, tz: str) -> SunTimes:
	z = ZoneInfo(tz)
	sr_utc = _solar_event(d, lat, lon, rising=True) or datetime(d.year, d.month, d.day, 6, tzinfo=timezone.utc)
	ss_utc = _solar_event(d, lat, lon, rising=False) or datetime(d.year, d.month, d.day, 18, tzinfo=timezone.utc)
	return SunTimes(sunrise=sr_utc.astimezone(z), sunset=ss_utc.astimezone(z))


def preset_times(preset: str, lat: float, lon: float, tz: str,
				 reference_date: date | None = None) -> tuple[str, str]:
	"""Resolve a preset name into HH:MM start/end strings."""
	today = reference_date or date.today()
	s_today = sun_times(today, lat, lon, tz)
	s_tomorrow = sun_times(today + timedelta(days=1), lat, lon, tz)

	def fmt(dt: datetime) -> str:
		return dt.strftime("%H:%M")

	if preset == "civil":
		return fmt(s_today.sunset + timedelta(minutes=30)), fmt(s_tomorrow.sunrise - timedelta(minutes=30))
	if preset == "astronomical":
		return fmt(s_today.sunset + timedelta(minutes=90)), fmt(s_tomorrow.sunrise - timedelta(minutes=90))
	if preset == "dusk-dawn":
		return fmt(s_today.sunset), fmt(s_tomorrow.sunrise)
	if preset == "evening-only":
		return fmt(s_today.sunset), "23:59"
	if preset == "morning-only":
		return "00:00", fmt(s_tomorrow.sunrise)
	raise ValueError(f"Unknown preset: {preset}")


PRESETS = [
	("civil",         "Civil twilight", "30 min after sunset to 30 min before sunrise. Best for migration."),
	("astronomical",  "Astronomical",   "90 min after sunset to 90 min before sunrise. Skips dusk chorus."),
	("dusk-dawn",     "Dusk to dawn",   "At sunset to at sunrise."),
	("evening-only",  "Evening only",   "At sunset to midnight."),
	("morning-only",  "Morning only",   "Midnight to sunrise."),
]
