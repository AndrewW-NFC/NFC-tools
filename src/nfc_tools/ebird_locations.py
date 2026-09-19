"""Optional public hotspot lookup. Personal locations require the user's eBird account."""
import os
import httpx

_hotspots: dict[str, dict] = {}

async def nearby_hotspots(latitude: float, longitude: float, api_key: str) -> list[dict]:
    key = api_key.strip() or os.environ.get("EBIRD_API_KEY", "")
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
