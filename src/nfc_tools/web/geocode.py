"""Optional location helpers for recorder-site coordinates."""

# Role: Resolves optional site location information for settings and import routes.
# Dependencies: HTTPX accesses Open-Meteo timezone lookup; callers supply coordinates.
from __future__ import annotations
import httpx


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
