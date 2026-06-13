"""CSV date/time formatting helpers.

NFC Tools writes dates and times as separate text fields in user-facing CSVs.
The leading apostrophe is an Excel text guard: Excel displays the value without
converting yyyy-mm-dd into a date serial or localized date format.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_datetime(value: Any | None = None) -> datetime:
    """Return a datetime from a datetime-like value, or now if unavailable."""
    if isinstance(value, datetime):
        return value
    if value is None or value == "":
        return datetime.now()

    text = str(value).strip()
    if text.startswith("'"):
        text = text[1:]

    # Accept normal NFC Tools API/status values. Keep CSV output separate.
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        pass

    # Date-only fallback.
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d")
    except Exception:
        return datetime.now()


def date_text(value: Any | None = None) -> str:
    return parse_datetime(value).strftime("%Y-%m-%d")


def time_text(value: Any | None = None) -> str:
    return parse_datetime(value).strftime("%H-%M-%S")


def split_date_time(value: Any | None = None) -> tuple[str, str]:
    dt = parse_datetime(value)
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H-%M-%S")


def excel_text(value: Any) -> str:
    """Return a plain-text CSV value protected from Excel auto-conversion.

    Excel strips the leading apostrophe for display but keeps the cell as text.
    The value is intentionally not written as a formula, such as ="2026-06-13".
    """
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if text.startswith("'"):
        return text
    return "'" + text


def unexcel_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return text[1:] if text.startswith("'") else text


def is_date_or_time_field(name: str) -> bool:
    key = str(name).strip().lower()
    return (
        key in {"date", "time", "session_date"}
        or key.endswith("_date")
        or key.endswith("_time")
    )


def guard_csv_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: excel_text(value) if is_date_or_time_field(key) else value
        for key, value in row.items()
    }


def unguard_csv_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        key: unexcel_text(value) if is_date_or_time_field(key) else ("" if value is None else str(value))
        for key, value in row.items()
    }
