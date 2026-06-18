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
        return "pre"
    if started_at + tolerance >= nfc_ends_at:
        return "post"
    return "nfc"


def seconds_until_next_segment_boundary(
    started_at: datetime,
    base_segment_seconds: int,
    nfc_starts_at: datetime,
    nfc_ends_at: datetime,
) -> int:
    """Return a segment length that stops at astronomical boundaries."""
    nfc_starts_at = _comparable(started_at, nfc_starts_at)
    nfc_ends_at = _comparable(started_at, nfc_ends_at)
    target = started_at + timedelta(seconds=max(1, int(base_segment_seconds)))
    for boundary in sorted((nfc_starts_at, nfc_ends_at, _next_midnight(started_at))):
        if started_at < boundary < target:
            target = boundary
            break
    return max(1, int((target - started_at).total_seconds() + 0.999999))
