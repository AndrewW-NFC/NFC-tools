"""Per-night CSV manifest for downstream tools and support diagnostics."""
from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

_FIELDS = [
    "session_date",
    "recorded_date",
    "recorded_time",
    "filename",
    "size_bytes",
    "started_date",
    "started_time",
    "finished_date",
    "finished_time",
    "analyzers",
    "statuses",
    "notes",
]
_lock = Lock()


def _parse_dt(value: Any | None) -> datetime | None:
    if isinstance(value, datetime):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _split(value: Any | None) -> tuple[str, str]:
    dt = _parse_dt(value)
    if not dt:
        return "", ""
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H-%M-%S")


def append(night_dir: Path, row: dict) -> None:
    path = night_dir / "manifest.csv"
    new = not path.exists()
    started_value = row.get("started_at") or datetime.now()
    finished_value = row.get("finished_at")
    recorded_value = row.get("recorded_at")
    started_date, started_time = _split(started_value)
    finished_date, finished_time = _split(finished_value)
    recorded_date, recorded_time = _split(recorded_value)

    normalized = {
        "session_date": row.get("session_date", ""),
        "recorded_date": row.get("recorded_date") or recorded_date,
        "recorded_time": row.get("recorded_time") or recorded_time,
        "filename": row.get("filename", ""),
        "size_bytes": row.get("size_bytes", ""),
        "started_date": row.get("started_date") or started_date,
        "started_time": row.get("started_time") or started_time,
        "finished_date": row.get("finished_date") or finished_date,
        "finished_time": row.get("finished_time") or finished_time,
        "analyzers": row.get("analyzers", ""),
        "statuses": row.get("statuses", ""),
        "notes": row.get("notes", ""),
    }
    with _lock, path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(normalized)


def read_all(night_dir: Path) -> list[dict]:
    path = night_dir / "manifest.csv"
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))
