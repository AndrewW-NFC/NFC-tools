"""Optional public hotspot lookup. Personal locations require the user's eBird account."""
import os
import tempfile
from pathlib import Path

import httpx

from .paths import config_dir

_hotspots: dict[str, dict] = {}

async def nearby_hotspots(latitude: float, longitude: float, api_key: str) -> list[dict]:
    supplied_key = api_key.strip()
    key = supplied_key or saved_api_key() or os.environ.get("EBIRD_API_KEY", "").strip()
    if not key:
        raise ValueError("Enter an eBird API key to search public hotspots. Recording does not require one.")
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("Enter valid recording coordinates first.")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get("https://api.ebird.org/v2/ref/hotspot/geo", params={
            "lat": latitude, "lng": longitude, "dist": 25, "fmt": "json",
        }, headers={"X-eBirdApiToken": key})
        response.raise_for_status()
    items = []
    for row in response.json():
        item = {k: row[k] for k in ("locId", "locName", "lat", "lng", "countryCode", "subnational1Code") if k in row}
        if all(k in item for k in ("locId", "locName", "lat", "lng")):
            items.append(item)
    if supplied_key:
        save_api_key(supplied_key)
    # Only canonical results returned by eBird can be selected by a form.
    if len(_hotspots) > 5000:
        _hotspots.clear()
    _hotspots.update({row["locId"]: row for row in items})
    return sorted(items, key=lambda row: row["locName"])


def selected_hotspot(hotspot_id: str, site) -> dict:
    saved = site.ebird_hotspot_details
    result = _hotspots.get(hotspot_id) or (saved if saved.get("locId") == hotspot_id else None)
    if not result:
        raise ValueError("Search and select a public hotspot before enabling public-hotspot exports.")
    return dict(result)


def _api_key_path() -> Path:
    # Separate from config.yaml so diagnostics and import plans never contain it.
    return config_dir() / "ebird-api-key"


def saved_api_key() -> str:
    try:
        return _api_key_path().read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


def save_api_key(key: str) -> None:
    path = _api_key_path()
    fd, temporary = tempfile.mkstemp(prefix=".ebird-key-", dir=path.parent)
    try:
        # mkstemp creates an owner-only file (0600 on POSIX). Atomic replacement
        # preserves that mode when replacing an older key.
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(key)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def forget_api_key() -> None:
    _api_key_path().unlink(missing_ok=True)


def api_key_status() -> dict:
    return {"saved": bool(saved_api_key()),
            "environment": bool(os.environ.get("EBIRD_API_KEY", "").strip())}
