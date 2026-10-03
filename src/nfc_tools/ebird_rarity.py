"""Local reviewer filters. Dates are annual, inclusive change points."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from datetime import date, datetime, timedelta, timezone

from pydantic import BaseModel, Field

RARITY_COMMENT = "Flagged rare for species and/or date. Provide recording or description of the call."
MAX_FILTER_BYTES = 2 * 1024 * 1024
MONTHS = {name: number for number, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}


class RarityFilter(BaseModel):
    region: str
    source: str
    imported_at: str
    sha256: str
    # MMDD and threshold; positive thresholds end zero periods but never flag counts.
    thresholds: dict[str, list[tuple[int, int]]]
    association: dict = Field(default_factory=dict)

    def evaluate(self, name: str, day: date) -> tuple[str, str]:
        points = self.thresholds.get(name)
        if not points:
            return "not evaluated", ""
        key = day.month * 100 + day.day
        index = max(i for i, (start, _) in enumerate(points) if start <= key)
        start, count = points[index]
        end = date(day.year, 12, 31)
        if index + 1 < len(points):
            next_start = points[index + 1][0]
            end = date(day.year, next_start // 100, next_start % 100) - timedelta(days=1)
        interval = f"{start // 100:02d}-{start % 100:02d} through {end:%m-%d}"
        return ("rare" if count == 0 else "not flagged"), interval

    def preview(self) -> list[tuple[str, str]]:
        result = []
        for name, points in self.thresholds.items():
            periods = [self.evaluate(name, date(2000, start // 100, start % 100))[1]
                       for start, count in points if count == 0]
            if periods:
                result.append((name, "; ".join(periods)))
            if len(result) == 5:
                break
        return result


def parse_filter(data: bytes, source: str, region: str) -> RarityFilter:
    if not region.strip():
        raise ValueError("Enter the region covered by the reviewer filter.")
    if len(data) > MAX_FILTER_BYTES:
        raise ValueError("Reviewer CSV must be no larger than 2 MB.")
    try:
        rows = csv.reader(io.StringIO(data.decode("utf-8-sig")), strict=True)
        thresholds = {}
        for line, row in enumerate(rows, 1):
            if not row or not any(cell.strip() for cell in row):
                continue
            row = [cell.strip() for cell in row]
            if len(row) < 3 or len(row) % 2 != 1 or not row[0]:
                raise ValueError(f"Row {line}: expected a species name followed by date/count pairs.")
            if row[0] in thresholds:
                raise ValueError(f"Row {line}: duplicate species name.")
            points = []
            for offset in range(1, len(row), 2):
                match = re.fullmatch(r"([A-Z][a-z]{2})\s+(\d{1,2})", row[offset])
                try:
                    if not match:
                        raise ValueError
                    month = MONTHS[match[1]]
                    day = int(match[2])
                    date(2000, month, day)
                    # An annual Feb 29 transition has no unambiguous non-leap-year equivalent.
                    if (month, day) == (2, 29):
                        raise ValueError
                    key = month * 100 + day
                    if not re.fullmatch(r"\d+", row[offset + 1]):
                        raise ValueError
                    count = int(row[offset + 1])
                except (ValueError, KeyError):
                    raise ValueError(f"Row {line}: invalid date/count pair; use dates such as Jan 1 and nonnegative whole counts (no Feb 29 change points).") from None
                if points and key <= points[-1][0]:
                    raise ValueError(f"Row {line}: dates must increase without duplicates.")
                points.append((key, count))
            if points[0][0] != 101:
                raise ValueError(f"Row {line}: the first threshold must begin Jan 1.")
            thresholds[row[0]] = points
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("Could not read the reviewer file as UTF-8 CSV.") from exc
    if not thresholds:
        raise ValueError("Reviewer CSV is empty.")
    return RarityFilter(region=region.strip(), source=source, imported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        sha256=hashlib.sha256(data).hexdigest(), thresholds=thresholds)


def site_association(site) -> dict:
    """Both the recording coordinates and the export location must be covered."""
    hotspot = site.ebird_hotspot_details if site.ebird_location_type == "hotspot" else {}
    return {"latitude": site.latitude, "longitude": site.longitude,
            "country": site.ebird_country_code, "state": site.ebird_state_province,
            "location_type": site.ebird_location_type,
            "hotspot_id": hotspot.get("locId", ""),
            "export_latitude": hotspot.get("lat", site.latitude),
            "export_longitude": hotspot.get("lng", site.longitude)}


def filter_for_site(site) -> RarityFilter | None:
    if not site.ebird_rarity_enabled or not site.exports_enabled:
        return None
    profile = site.ebird_rarity_filter
    if profile is None or profile.association != site_association(site):
        raise ValueError("Confirm reviewer filter coverage for this location in Settings before exporting.")
    return profile


def annotate(comment: str, profile: RarityFilter | None, name: str, day: date) -> str:
    if profile and profile.evaluate(name, day)[0] == "rare" and RARITY_COMMENT not in comment:
        return f"{comment} | {RARITY_COMMENT}" if comment else RARITY_COMMENT
    return comment
