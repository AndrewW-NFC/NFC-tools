"""Filename parsing. One source of truth for the recording naming convention.

Format: <prefix>_<sessionDate>_<YYYY-MM-DD>_<HH-MM-SS>.wav
Example: NFC_2026-05-10_2026-05-11_03-22-14.wav
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta

_CURRENT = re.compile(
	r"^(?P<prefix>[A-Za-z0-9]+)_"
	r"(?P<session>\d{4}-\d{2}-\d{2})_"
	r"(?P<rec_date>\d{4}-\d{2}-\d{2})_"
	r"(?P<hh>\d{2})-(?P<mm>\d{2})-(?P<ss>\d{2})$"
)
# Legacy: "NFCs starting 2026-05-11 03-22-14.wav"
_LEGACY = re.compile(
	r"^NFCs starting "
	r"(?P<rec_date>\d{4}-\d{2}-\d{2}) "
	r"(?P<hh>\d{2})-(?P<mm>\d{2})-(?P<ss>\d{2})$"
)


@dataclass
class ParsedName:
	prefix: str
	session_date: date
	recorded_at: datetime
	stem: str
	is_legacy: bool

	@property
	def filename(self) -> str:
		return (
			f"{self.prefix}_{self.session_date.isoformat()}_"
			f"{self.recorded_at.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
		)


def parse(name: str) -> ParsedName | None:
	stem = name
	for ext in (".wav", ".WAV"):
		if stem.endswith(ext):
			stem = stem[: -len(ext)]
			break

	m = _CURRENT.match(stem)
	if m:
		return ParsedName(
			prefix=m["prefix"],
			session_date=date.fromisoformat(m["session"]),
			recorded_at=datetime(
				*map(int, m["rec_date"].split("-")),
				int(m["hh"]), int(m["mm"]), int(m["ss"]),
			),
			stem=stem,
			is_legacy=False,
		)
	m = _LEGACY.match(stem)
	if m:
		rec_date = date.fromisoformat(m["rec_date"])
		rec_time = time(int(m["hh"]), int(m["mm"]), int(m["ss"]))
		session = rec_date - timedelta(days=1) if rec_time.hour < 12 else rec_date
		return ParsedName(
			prefix="NFCs",
			session_date=session,
			recorded_at=datetime.combine(rec_date, rec_time),
			stem=stem,
			is_legacy=True,
		)
	return None


def make(prefix: str, session_date: date, recorded_at: datetime) -> str:
	return ParsedName(
		prefix=prefix, session_date=session_date,
		recorded_at=recorded_at, stem="", is_legacy=False,
	).filename
