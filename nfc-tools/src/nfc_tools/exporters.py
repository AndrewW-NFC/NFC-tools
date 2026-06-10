"""Export detections to CSV (rich) and to eBird-import format."""
from __future__ import annotations
import csv
import io
from datetime import datetime
from typing import Iterable

from .config import Config
from .detections import Detection


_RICH_COLUMNS = [
	"session_date", "timestamp", "filename", "analyzer",
	"species", "common_name", "confidence",
	"start_seconds", "end_seconds",
]

_EBIRD_COLUMNS = [
	"Common Name", "Genus", "Species", "Number", "Species Comments",
	"Location Name", "Latitude", "Longitude", "Date", "Start Time",
	"State/Province", "Country Code", "Protocol", "Number of Observers",
	"Duration", "All observations reported?", "Effort Distance Miles",
	"Effort area acres", "Submission Comments",
]


def to_rich_csv(rows: Iterable[Detection]) -> str:
	out = io.StringIO()
	w = csv.DictWriter(out, fieldnames=_RICH_COLUMNS, extrasaction="ignore")
	w.writeheader()
	for r in rows:
		w.writerow(r.to_dict())
	return out.getvalue()


def to_ebird_csv(rows: Iterable[Detection], cfg: Config,
				 min_confidence: float = 0.7) -> str:
	rows = [r for r in rows if r.confidence >= min_confidence]
	if not rows:
		return _empty_ebird_csv()

	by_species: dict[str, list[Detection]] = {}
	for r in rows:
		by_species.setdefault(r.common_name or r.species, []).append(r)

	first = min(rows, key=lambda r: r.timestamp or "9999")
	last = max(rows, key=lambda r: r.timestamp or "")
	try:
		t_first = datetime.fromisoformat(first.timestamp) if first.timestamp else None
		t_last = datetime.fromisoformat(last.timestamp) if last.timestamp else None
		duration_min = int((t_last - t_first).total_seconds() // 60) if t_first and t_last else ""
		date_str = t_first.strftime("%m/%d/%Y") if t_first else ""
		start_time = t_first.strftime("%I:%M %p").lstrip("0") if t_first else ""
	except Exception:
		duration_min = ""; date_str = ""; start_time = ""

	out = io.StringIO()
	w = csv.DictWriter(out, fieldnames=_EBIRD_COLUMNS, extrasaction="ignore")
	w.writeheader()
	for name, group in sorted(by_species.items()):
		first_g = min(group, key=lambda r: r.start_seconds)
		sci = first_g.species or ""
		genus, _, sp = sci.partition(" ")
		w.writerow({
			"Common Name": name,
			"Genus": genus,
			"Species": sp,
			"Number": len(group),
			"Species Comments": (
				f"Auto-detected by {first_g.analyzer}; max confidence "
				f"{max(g.confidence for g in group):.2f}. Review before submitting."
			),
			"Location Name": cfg.site.name,
			"Latitude": cfg.site.latitude,
			"Longitude": cfg.site.longitude,
			"Date": date_str,
			"Start Time": start_time,
			"Protocol": "Stationary",
			"Number of Observers": 1,
			"Duration": duration_min,
			"All observations reported?": "N",
			"Submission Comments": (
				"Recorded with NFC Tools. Detections are automated and may include "
				"errors; this checklist is a draft for review."
			),
		})
	return out.getvalue()


def _empty_ebird_csv() -> str:
	out = io.StringIO()
	csv.DictWriter(out, fieldnames=_EBIRD_COLUMNS).writeheader()
	return out.getvalue()
