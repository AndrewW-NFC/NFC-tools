"""Helpers for NFC-window segment naming and split points."""
from __future__ import annotations

from datetime import datetime, timedelta


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _comparable(reference: datetime, value: datetime) -> datetime:
    """Return value in the same timezone style as reference."""
    reference_aware = _is_aware(reference)
    value_aware = _is_aware(value)
    if reference_aware and value_aware:
        return value.astimezone(reference.tzinfo)
    if reference_aware and not value_aware:
        return value.replace(tzinfo=reference.tzinfo)
    if not reference_aware and value_aware:
        return value.replace(tzinfo=None)
    return value


def _next_midnight(started_at: datetime) -> datetime:
    tomorrow = started_at.date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=started_at.tzinfo)


def segment_period_for_start(
    started_at: datetime,
    nfc_starts_at: datetime,
    nfc_ends_at: datetime,
    *,
    boundary_tolerance_seconds: int = 2,
) -> str:
    """Classify a recording segment by its start time."""
    nfc_starts_at = _comparable(started_at, nfc_starts_at)
    nfc_ends_at = _comparable(started_at, nfc_ends_at)
    tolerance = timedelta(seconds=max(0, int(boundary_tolerance_seconds)))
    if started_at + tolerance < nfc_starts_at:
        return "civil_evening"
    if started_at + tolerance >= nfc_ends_at:
        return "civil_morning"
    return "nfc"


def seconds_until_next_segment_boundary(
    started_at: datetime,
    base_segment_seconds: int,
    nfc_starts_at: datetime,
    nfc_ends_at: datetime,
    civil_starts_at: datetime | None = None,
    civil_ends_at: datetime | None = None,
) -> int:
    """Return a segment length that stops at protocol and midnight boundaries."""
    nfc_starts_at = _comparable(started_at, nfc_starts_at)
    nfc_ends_at = _comparable(started_at, nfc_ends_at)
    boundaries = [nfc_starts_at, nfc_ends_at, _next_midnight(started_at)]
    if civil_starts_at:
        boundaries.append(_comparable(started_at, civil_starts_at))
    if civil_ends_at:
        boundaries.append(_comparable(started_at, civil_ends_at))
    target = started_at + timedelta(seconds=max(1, int(base_segment_seconds)))
    for boundary in sorted(boundaries):
        if started_at < boundary < target:
            target = boundary
            break
    return max(1, int((target - started_at).total_seconds() + 0.999999))


def recording_period_and_seconds(started_at: datetime, base_seconds: float, site) -> tuple[str, float]:
    """Resolve each segment against its local day's solar events, including long recordings."""
    import math
    from datetime import timezone
    from zoneinfo import ZoneInfo
    from .ephemeris import sun_times

    zone = ZoneInfo(site.timezone)
    local = started_at.astimezone(zone) if _is_aware(started_at) else started_at.replace(tzinfo=zone)
    sun = sun_times(local.date(), site.latitude, site.longitude, site.timezone)
    morning_end = sun.sunrise + timedelta(hours=2)
    # Recording filenames have second precision; permit subsecond capture handoff.
    at = local + timedelta(seconds=2)
    if at < sun.astronomical_dawn:
        period = "nfc"
    elif at < sun.civil_dawn:
        period = "civil_morning"
    elif at < morning_end:
        period = "morning_flight"
    elif at < sun.civil_dusk:
        period = "daytime"
    elif at < sun.astronomical_dusk:
        period = "civil_evening"
    else:
        period = "nfc"
    midnight = _next_midnight(local)
    noon = local.replace(hour=12, minute=0, second=0, microsecond=0)
    boundaries = [sun.astronomical_dawn, sun.civil_dawn, morning_end,
                  sun.civil_dusk, sun.astronomical_dusk, midnight, noon]
    distances = [(b.astimezone(timezone.utc) - local.astimezone(timezone.utc)).total_seconds()
                 for b in boundaries]
    seconds = min(base_seconds, *(math.ceil(d) for d in distances if d > 0.001))
    return period, seconds
