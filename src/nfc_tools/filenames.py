"""Filename parsing. One source of truth for the recording naming convention.

Format: <index>_<period>_<YYYY-MM-DD>_<HH-MM-SS>.wav
Legacy prefix-based names remain readable.
Example: 001_NFC_2026-05-11_03-22-14.wav
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from pathlib import Path

INDEX_WIDTH = 3
PERIODS = {"nfc", "civil_evening", "civil_morning", "morning_flight", "daytime"}
_PERIOD_NAME = re.compile(
    r"^(?:(?P<index>\d+)_)?(?P<period>NFC|CIVIL_EVENING|CIVIL_MORNING|MORNING_FLIGHT|DAYTIME)_"
    r"(?P<stamp>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$"
)

_CURRENT = re.compile(
    r"^(?:(?P<index>\d+)_)?"
    r"(?P<prefix>[A-Za-z0-9]+)_"
    r"(?:(?P<period>[A-Z][A-Z0-9_]*)_)?"
    r"(?P<rec_date>\d{4}-\d{2}-\d{2})_"
    r"(?P<hh>\d{2})-(?P<mm>\d{2})-(?P<ss>\d{2})$"
)
# Compatibility for recordings made while filenames carried both the session
# date and recording date. New filenames intentionally use only rec_date.
_SESSION_DATED = re.compile(
    r"^(?:(?P<index>\d+)_)?"
    r"(?P<prefix>[A-Za-z0-9]+)_"
    r"(?:(?P<period>[A-Z][A-Z0-9_]*)_)?"
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
    period: str = "nfc"
    index: int | None = None

    @property
    def filename(self) -> str:
        label = self.period.upper()
        index_prefix = "" if self.index is None else f"{self.index:0{INDEX_WIDTH}d}_"
        return (
            f"{index_prefix}{label}_"
            f"{self.recorded_at.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
        )


def parse(name: str) -> ParsedName | None:
    stem = name
    for ext in (".wav", ".WAV"):
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break

    m = _PERIOD_NAME.match(stem)
    if m:
        recorded = datetime.strptime(m["stamp"], "%Y-%m-%d_%H-%M-%S")
        return ParsedName(
            prefix="NFC", session_date=recorded.date() - timedelta(days=1) if recorded.hour < 12 else recorded.date(),
            recorded_at=recorded, stem=stem, is_legacy=False, period=m["period"].lower(),
            index=int(m["index"]) if m["index"] else None,
        )
    m = _CURRENT.match(stem)
    if m:
        rec_date = date.fromisoformat(m["rec_date"])
        rec_time = time(int(m["hh"]), int(m["mm"]), int(m["ss"]))
        return ParsedName(
            prefix=m["prefix"],
            session_date=rec_date - timedelta(days=1) if rec_time.hour < 12 else rec_date,
            recorded_at=datetime.combine(rec_date, rec_time),
            stem=stem,
            is_legacy=False,
            period=(m["period"] or "nfc").lower(),
            index=int(m["index"]) if m["index"] else None,
        )
    m = _SESSION_DATED.match(stem)
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
            period=(m["period"] or "nfc").lower(),
            index=int(m["index"]) if m["index"] else None,
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
            period="nfc",
        )
    return None


def make(
    prefix: str,
    session_date: date,
    recorded_at: datetime,
    period: str = "nfc",
    index: int | None = None,
) -> str:
    normalized_period = (period or "nfc").lower()
    if normalized_period not in PERIODS:
        raise ValueError(f"Unknown recording period: {period}")
    if index is not None and index < 1:
        raise ValueError(f"Recording index must be positive: {index}")
    return ParsedName(
        prefix=prefix, session_date=session_date,
        recorded_at=recorded_at, stem="", is_legacy=False,
        period=normalized_period,
        index=index,
    ).filename


def next_index_for_directory(audio_dir: Path) -> int:
    """Return the next recording index for a night audio directory."""
    if not audio_dir.exists():
        return 1

    recognized = []
    max_index = 0
    for path in audio_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".wav":
            continue
        parsed = parse(path.name)
        if not parsed:
            continue
        recognized.append(parsed)
        if parsed.index is not None:
            max_index = max(max_index, parsed.index)

    if max_index:
        return max(max_index, len(recognized)) + 1
    return len(recognized) + 1
