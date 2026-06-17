"""Helpers for NFC-window segment naming and split points."""
from __future__ import annotations

from datetime import datetime, timedelta


def segment_period_for_start(started_at: datetime, nfc_starts_at: datetime, nfc_ends_at: datetime) -> str:
    """Classify a recording segment by its start time."""
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
    target = started_at + timedelta(seconds=max(1, int(base_segment_seconds)))
    for boundary in (nfc_starts_at, nfc_ends_at):
        if started_at < boundary < target:
            target = boundary
            break
    return max(1, int(round((target - started_at).total_seconds())))
