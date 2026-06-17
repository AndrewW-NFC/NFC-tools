"""CSV-backed session log helpers for the local dashboard."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import night_dir, recordings_root

SESSION_LOG_FIELDS = [
    "date",
    "time",
    "event",
    "message",
    "session_date",
    "state",
    "filename",
    "analyzer",
    "level_db",
    "details",
]


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def _split_datetime(value: Any | None = None) -> tuple[str, str, str]:
    """Return CSV date, CSV time, and UI timestamp.

    CSV files use separate plain-text date/time columns. The dashboard still
    receives an ISO-like timestamp string for browser-side display only.
    """
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or "").strip()
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                dt = datetime.now()
        else:
            dt = datetime.now()
    date_text = dt.strftime("%Y-%m-%d")
    time_text = dt.strftime("%H-%M-%S")
    timestamp = f"{date_text}T{dt.strftime('%H:%M:%S')}"
    return date_text, time_text, timestamp


def _timestamp_from_row(row: dict[str, str]) -> str:
    if row.get("timestamp"):
        return row["timestamp"]
    date_text = row.get("date", "")
    time_text = row.get("time", "")
    if date_text and time_text:
        return f"{date_text}T{time_text.replace('-', ':')}"
    return ""


def log_path_for_session_date(session_date: str) -> Path:
    return night_dir(session_date) / "logs" / "session_log.csv"


def latest_log_path() -> Path | None:
    roots = sorted(
        [p for p in recordings_root().iterdir() if p.is_dir()],
        key=lambda p: p.name,
        reverse=True,
    )
    for nd in roots:
        candidate = nd / "logs" / "session_log.csv"
        if candidate.exists():
            return candidate
    return None


def append_log_row(path: Path, row: dict[str, Any]) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    date_text, time_text, timestamp = _split_datetime(row.get("timestamp"))
    normalized = {field: _stringify(row.get(field, "")) for field in SESSION_LOG_FIELDS}
    normalized["date"] = _stringify(row.get("date") or date_text)
    normalized["time"] = _stringify(row.get("time") or time_text)

    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SESSION_LOG_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(normalized)

    normalized["timestamp"] = timestamp
    return normalized


def read_log_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["timestamp"] = _timestamp_from_row(row)
    if limit is not None:
        rows = rows[-limit:]
    return rows
