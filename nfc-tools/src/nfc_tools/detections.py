"""Parse analyzer outputs into a uniform Detection record.

We deliberately keep this lazy and tolerant: each analyzer's output
format may vary by version, and we'd rather skip a malformed row than
crash the whole results page.
"""
from __future__ import annotations
import csv
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from .filenames import parse as parse_filename
from .logging_setup import get
from .paths import night_dir

log = get("detections")


@dataclass
class Detection:
	session_date: str
	filename: str
	analyzer: str
	species: str
	common_name: str
	start_seconds: float
	end_seconds: float
	confidence: float
	timestamp: Optional[str] = None  # ISO 8601 if computable

	def to_dict(self) -> dict:
		return asdict(self)

	@property
	def clip_id(self) -> str:
		return f"{self.filename}|{self.analyzer}|{self.start_seconds:.2f}|{self.species}"


# ----- BirdNET -----

def _parse_birdnet_csv(path: Path, filename: str, session_date: str,
					   recorded_at: Optional[datetime]) -> Iterable[Detection]:
	try:
		with path.open() as f:
			reader = csv.DictReader(f)
			for row in reader:
				try:
					start = float(row.get("Start (s)") or row.get("start_s") or 0)
					end = float(row.get("End (s)") or row.get("end_s") or start + 3)
					sci = (row.get("Scientific name") or row.get("scientific_name") or "").strip()
					com = (row.get("Common name") or row.get("common_name") or "").strip()
					conf = float(row.get("Confidence") or row.get("confidence") or 0)
				except (ValueError, KeyError):
					continue
				if not sci and not com:
					continue
				ts = (recorded_at + timedelta(seconds=start)).isoformat() if recorded_at else None
				yield Detection(
					session_date=session_date, filename=filename, analyzer="birdnet",
					species=sci, common_name=com,
					start_seconds=start, end_seconds=end,
					confidence=conf, timestamp=ts,
				)
	except Exception as e:  # noqa: BLE001
		log.warning("could not parse %s: %s", path, e)


# ----- Nighthawk -----

# Nighthawk's Audacity label format: "<start>\t<end>\t<label>"
_NH_LABEL = re.compile(r"^(?P<name>.+?)[_ ](?P<conf>\d+(?:\.\d+)?)\s*$")


def _parse_nighthawk_txt(path: Path, filename: str, session_date: str,
						 recorded_at: Optional[datetime]) -> Iterable[Detection]:
	try:
		with path.open() as f:
			for line in f:
				parts = line.rstrip("\n").split("\t")
				if len(parts) < 3:
					continue
				try:
					start = float(parts[0]); end = float(parts[1])
				except ValueError:
					continue
				label = parts[2].strip()
				m = _NH_LABEL.match(label)
				if m:
					name = m.group("name").strip()
					try: conf = float(m.group("conf"))
					except ValueError: conf = 0.0
				else:
					name = label; conf = 0.0
				ts = (recorded_at + timedelta(seconds=start)).isoformat() if recorded_at else None
				yield Detection(
					session_date=session_date, filename=filename, analyzer="nighthawk",
					species=name, common_name=name,
					start_seconds=start, end_seconds=end,
					confidence=conf, timestamp=ts,
				)
	except Exception as e:  # noqa: BLE001
		log.warning("could not parse %s: %s", path, e)


# ----- Aggregator -----

def collect_for_night(session_date: str, min_confidence: float = 0.0,
					  analyzer: Optional[str] = None,
					  species: Optional[str] = None) -> list[Detection]:
	nd = night_dir(session_date)
	audio = nd / "audio"
	results = nd / "results"
	if not results.exists():
		return []

	out: list[Detection] = []
	for wav in audio.glob("*.wav"):
		parsed = parse_filename(wav.name)
		recorded_at = parsed.recorded_at if parsed else None
		stem = wav.stem

		if analyzer in (None, "birdnet"):
			bn_dir = results / "birdnet" / stem
			if bn_dir.exists():
				for csvf in bn_dir.glob("*.csv"):
					out.extend(_parse_birdnet_csv(csvf, wav.name, session_date, recorded_at))

		if analyzer in (None, "nighthawk"):
			nh_dir = results / "nighthawk" / stem
			if nh_dir.exists():
				for txt in nh_dir.glob("*.txt"):
					out.extend(_parse_nighthawk_txt(txt, wav.name, session_date, recorded_at))

	if min_confidence > 0:
		out = [d for d in out if d.confidence >= min_confidence]
	if species:
		s = species.lower()
		out = [d for d in out if s in d.species.lower() or s in d.common_name.lower()]

	out.sort(key=lambda d: (d.timestamp or "", d.filename, d.start_seconds))
	return out


def species_summary(detections: list[Detection]) -> list[dict]:
	buckets: dict[tuple[str, str, str], dict] = {}
	for d in detections:
		key = (d.analyzer, d.species, d.common_name)
		b = buckets.setdefault(key, {
			"analyzer": d.analyzer, "species": d.species, "common_name": d.common_name,
			"count": 0, "max_conf": 0.0, "first": None, "last": None,
		})
		b["count"] += 1
		b["max_conf"] = max(b["max_conf"], d.confidence)
		if d.timestamp:
			if not b["first"] or d.timestamp < b["first"]: b["first"] = d.timestamp
			if not b["last"]  or d.timestamp > b["last"]:  b["last"]  = d.timestamp
	rows = list(buckets.values())
	rows.sort(key=lambda r: (-r["count"], r["common_name"] or r["species"]))
	return rows
