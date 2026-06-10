"""Per-night CSV manifest for downstream tooling and the results browser."""
from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path
from threading import Lock

_FIELDS = [
	"session_date", "recorded_at", "filename", "size_bytes",
	"started_at", "finished_at", "analyzers", "statuses", "notes",
]
_lock = Lock()


def append(night_dir: Path, row: dict) -> None:
	path = night_dir / "manifest.csv"
	new = not path.exists()
	with _lock, path.open("a", newline="") as f:
		w = csv.DictWriter(f, fieldnames=_FIELDS, extrasaction="ignore")
		if new:
			w.writeheader()
		row.setdefault("started_at", datetime.now().isoformat(timespec="seconds"))
		w.writerow(row)


def read_all(night_dir: Path) -> list[dict]:
	path = night_dir / "manifest.csv"
	if not path.exists():
		return []
	with path.open() as f:
		return list(csv.DictReader(f))
