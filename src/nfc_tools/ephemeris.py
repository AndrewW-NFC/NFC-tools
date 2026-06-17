"""Sun and twilight computation using NOAA's algorithm.

We avoid heavy astronomy libraries; this is good to roughly a minute for
recording-window scheduling. Returned times are local clock times for the
given timezone.
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
    civil_dawn: datetime
    civil_dusk: datetime
    astronomical_dawn: datetime
    astronomical_dusk: datetime


SUNRISE_SUNSET_ZENITH = 90.833
CIVIL_TWILIGHT_ZENITH = 96.0
ASTRONOMICAL_TWILIGHT_ZENITH = 108.0
ASTRONOMICAL_RECORDING_BUFFER = timedelta(minutes=90)


def _solar_event(d: date, lat: float, lon: float, rising: bool, zenith: float = SUNRISE_SUNSET_ZENITH) -> datetime | None:
    """Return UTC datetime when the sun crosses zenith on date d.

    rising=True gives the morning crossing; rising=False gives the evening
    crossing. Standard sunrise/sunset uses 90.833 degrees. Civil twilight uses
    96 degrees, and astronomical twilight uses 108 degrees.
    """
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
    cosH = ((math.cos(math.radians(zenith)) - (sinDec * math.sin(math.radians(lat))))
            / (cosDec * math.cos(math.radians(lat))))
    if cosH > 1 or cosH < -1:
        return None
    H = (360 - math.degrees(math.acos(cosH))) if rising else math.degrees(math.acos(cosH))
    H = H / 15
    T = H + RA - (0.06571 * t) - 6.622
    ut_hours = T - lng_hour
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(hours=ut_hours)


def sun_times(d: date, lat: float, lon: float, tz: str) -> SunTimes:
    z = ZoneInfo(tz)
    fallback_dawn = datetime(d.year, d.month, d.day, 6, tzinfo=timezone.utc)
    fallback_dusk = datetime(d.year, d.month, d.day, 18, tzinfo=timezone.utc)
    sr_utc = _solar_event(d, lat, lon, rising=True) or fallback_dawn
    ss_utc = _solar_event(d, lat, lon, rising=False) or fallback_dusk
    civil_dawn_utc = _solar_event(d, lat, lon, rising=True, zenith=CIVIL_TWILIGHT_ZENITH) or sr_utc
    civil_dusk_utc = _solar_event(d, lat, lon, rising=False, zenith=CIVIL_TWILIGHT_ZENITH) or ss_utc
    astro_dawn_utc = _solar_event(d, lat, lon, rising=True, zenith=ASTRONOMICAL_TWILIGHT_ZENITH) or civil_dawn_utc
    astro_dusk_utc = _solar_event(d, lat, lon, rising=False, zenith=ASTRONOMICAL_TWILIGHT_ZENITH) or civil_dusk_utc
    return SunTimes(
        sunrise=sr_utc.astimezone(z),
        sunset=ss_utc.astimezone(z),
        civil_dawn=civil_dawn_utc.astimezone(z),
        civil_dusk=civil_dusk_utc.astimezone(z),
        astronomical_dawn=astro_dawn_utc.astimezone(z),
        astronomical_dusk=astro_dusk_utc.astimezone(z),
    )


def astronomical_nfc_window(d: date, lat: float, lon: float, tz: str) -> tuple[datetime, datetime]:
    """Return astronomical dusk and next astronomical dawn for an NFC night."""
    s_today = sun_times(d, lat, lon, tz)
    s_tomorrow = sun_times(d + timedelta(days=1), lat, lon, tz)
    return s_today.astronomical_dusk, s_tomorrow.astronomical_dawn


def astronomical_recording_window(d: date, lat: float, lon: float, tz: str) -> tuple[datetime, datetime]:
    """Return the broader recording window around the astronomical NFC window."""
    starts_at, ends_at = astronomical_nfc_window(d, lat, lon, tz)
    return starts_at - ASTRONOMICAL_RECORDING_BUFFER, ends_at + ASTRONOMICAL_RECORDING_BUFFER


def preset_times(preset: str, lat: float, lon: float, tz: str,
                 reference_date: date | None = None) -> tuple[str, str]:
    """Resolve a preset name into HH:MM start/end strings."""
    today = reference_date or date.today()
    s_today = sun_times(today, lat, lon, tz)
    s_tomorrow = sun_times(today + timedelta(days=1), lat, lon, tz)

    def fmt(dt: datetime) -> str:
        return dt.strftime("%H:%M")

    if preset == "astronomical":
        start, end = astronomical_recording_window(today, lat, lon, tz)
        return fmt(start), fmt(end)
    if preset == "civil":
        return fmt(s_today.civil_dusk), fmt(s_tomorrow.civil_dawn)
    if preset == "dusk-dawn":
        return fmt(s_today.sunset), fmt(s_tomorrow.sunrise)
    if preset == "evening-only":
        return fmt(s_today.sunset), "23:59"
    if preset == "morning-only":
        return "00:00", fmt(s_tomorrow.sunrise)
    raise ValueError(f"Unknown preset: {preset}")


PRESETS = [
    ("astronomical", "Astronomical twilight", "Records 90 minutes before astronomical dusk through 90 minutes after astronomical dawn; NFC files are split at astronomical twilight."),
    ("civil", "Civil twilight", "Civil dusk to civil dawn. Use separate checklists for civil-to-astronomical twilight periods."),
    ("dusk-dawn", "Sunset to sunrise", "Broader than the standard NFC protocol window."),
    ("evening-only", "Evening only", "Sunset to midnight; includes pre-astronomical twilight."),
    ("morning-only", "Morning only", "Midnight to sunrise; includes post-astronomical twilight."),
]
