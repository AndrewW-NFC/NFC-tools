"""Optional location helpers for recorder-site coordinates."""
from __future__ import annotations
from typing import Optional
import httpx


def lookup(query: str) -> Optional[dict]:
    if not query.strip():
        return None
    try:
        r = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            timeout=6,
        )
        r.raise_for_status()
        results = r.json().get("results") or []
        if not results:
            return None
        x = results[0]
        admin = f", {x['admin1']}" if x.get("admin1") else ""
        country = f", {x['country']}" if x.get("country") else ""
        return {
            "name": f"{x.get('name','')}{admin}{country}",
            "latitude": x["latitude"],
            "longitude": x["longitude"],
            "timezone": x.get("timezone") or "UTC",
        }
    except Exception:  # noqa: BLE001
        return None


def timezone_for_coordinates(latitude: float, longitude: float) -> str | None:
    try:
        r = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": latitude, "longitude": longitude, "timezone": "auto"},
            timeout=6,
        )
        r.raise_for_status()
        timezone = r.json().get("timezone")
        return str(timezone) if timezone else None
    except Exception:  # noqa: BLE001
        return None
