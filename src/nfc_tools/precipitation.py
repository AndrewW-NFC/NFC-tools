"""Comparable overnight model estimates; never total recording-start snapshots.

Contract overnight-precipitation-v1 is also implemented in the acoustic app's
precipitation.js. UTC interval ends prevent duplicate DST hours and restarts
from counting an accumulation twice. Source observations are not claimed.
"""
from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .weather import _weather_json

CONTRACT = "overnight-precipitation-v1"
SOURCE = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "ecmwf_ifs"


def night_window(evening: str, tz: str) -> tuple[datetime, datetime]:
    day = date.fromisoformat(evening)
    zone = ZoneInfo(tz)
    return (datetime.combine(day, time(18), zone),
            datetime.combine(day + timedelta(days=1), time(6), zone))


def summarize_payload(data: dict, evening: str, lat: float, lon: float, tz: str,
                      *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    start, end = night_window(evening, tz)
    first, last = int(start.timestamp()), int(end.timestamp())
    expected = list(range(first + 3600, last + 1, 3600))
    hourly = data.get("hourly", {})
    values = hourly.get("precipitation", [])
    by_end: dict[int, list] = {}
    for i, stamp in enumerate(hourly.get("time", [])):
        if isinstance(stamp, (int, float)) and stamp in expected:
            by_end.setdefault(stamp, []).append(values[i] if i < len(values) else None)
    unit_ok = data.get("hourly_units", {}).get("precipitation") == "mm"
    intervals = []
    for stamp in expected:
        candidates = by_end.get(stamp, [])
        valid = (unit_ok and bool(candidates) and all(
            isinstance(v, (int, float)) and not isinstance(v, bool)
            and math.isfinite(v) and v >= 0 for v in candidates)
            and len(set(candidates)) == 1)
        intervals.append({"interval_start_utc": datetime.fromtimestamp(stamp - 3600, timezone.utc).isoformat(),
                          "interval_end_utc": datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
                          "precipitation_mm": candidates[0] if valid else None})
    valid_values = [r["precipitation_mm"] for r in intervals if r["precipitation_mm"] is not None]
    complete = now.timestamp() >= last and len(valid_values) == len(expected)
    total = round(sum(valid_values), 6) if complete else None
    return {
        "contract": CONTRACT, "evening_date": evening,
        "source": SOURCE, "model": MODEL, "data_kind": "modeled_estimate",
        "latitude": lat, "longitude": lon, "timezone": tz,
        "grid_latitude": data.get("latitude"), "grid_longitude": data.get("longitude"),
        "grid_elevation_m": data.get("elevation"),
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "retrieved_at_utc": now.astimezone(timezone.utc).isoformat(),
        "status": "complete" if complete else "in_progress" if now.timestamp() < last else "incomplete",
        "expected_hours": len(expected), "available_hours": len(valid_values),
        "total_mm": total, "total_in": round(total / 25.4, 6) if total is not None else None,
        "available_subtotal_mm": round(sum(valid_values), 6),
        "intervals": intervals,
    }


def fetch_summary(evening: str, lat: float, lon: float, tz: str) -> dict:
    start, end = night_window(evening, tz)
    now = datetime.now(timezone.utc)
    if now.timestamp() < end.timestamp():
        return summarize_payload({}, evening, lat, lon, tz, now=now)
    if start.year < 2017:
        raise ValueError("The shared ECMWF IFS precipitation source starts in 2017.")
    data = _weather_json(SOURCE, {
        "latitude": lat, "longitude": lon, "hourly": "precipitation",
        "models": MODEL, "precipitation_unit": "mm", "timezone": "UTC",
        "timeformat": "unixtime", "cell_selection": "land",
        "start_date": start.astimezone(timezone.utc).date().isoformat(),
        "end_date": end.astimezone(timezone.utc).date().isoformat(),
    })
    return summarize_payload(data, evening, lat, lon, tz)


def refresh_night(night_path: Path) -> dict:
    """Use the saved site's identity, never silently substitute current settings."""
    with (night_path / "logs" / "environmental_conditions.csv").open(newline="", encoding="utf-8") as handle:
        sites = {(float(r["latitude"]), float(r["longitude"]), r["timezone"])
                 for r in csv.DictReader(handle)}
    if len(sites) != 1:
        raise ValueError("A precipitation summary requires exactly one saved recording location and timezone.")
    lat, lon, tz = sites.pop()
    result = fetch_summary(night_path.name, lat, lon, tz)
    path = night_path / "logs" / "overnight_precipitation.json"
    fd, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, allow_nan=False)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return result


def saved_summary(night_path: Path) -> dict | None:
    path = night_path / "logs" / "overnight_precipitation.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
