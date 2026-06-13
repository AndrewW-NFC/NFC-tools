"""CSV-backed session log helpers for the local dashboard."""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import night_dir, recordings_root

SESSION_LOG_FIELDS = [
    "timestamp",
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
    normalized = {field: _stringify(row.get(field, "")) for field in SESSION_LOG_FIELDS}
    if not normalized["timestamp"]:
        normalized["timestamp"] = datetime.now().isoformat(timespec="seconds")

    write_header = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SESSION_LOG_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(normalized)
    return normalized


def read_log_rows(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if limit is not None:
        rows = rows[-limit:]
    return rows
