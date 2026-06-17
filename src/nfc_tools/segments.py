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


def segment_period_for_start(started_at: datetime, nfc_starts_at: datetime, nfc_ends_at: datetime) -> str:
    """Classify a recording segment by its start time."""
    nfc_starts_at = _comparable(started_at, nfc_starts_at)
    nfc_ends_at = _comparable(started_at, nfc_ends_at)
    if started_at < nfc_starts_at:
        return "pre"
    if started_at >= nfc_ends_at:
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
    for boundary in (nfc_starts_at, nfc_ends_at):
        if started_at < boundary < target:
            target = boundary
            break
    return max(1, int(round((target - started_at).total_seconds())))
