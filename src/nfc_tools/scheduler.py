"""Compute session timing windows. Pure functions; easy to test."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


@dataclass
class SessionWindow:
	session_date: date
	starts_at: datetime
	ends_at: datetime

	@property
	def crosses_midnight(self) -> bool:
		return self.starts_at.date() != self.ends_at.date()


def parse_hhmm(s: str) -> time:
	h, m = s.split(":")
	return time(int(h), int(m))


def session_date_for(now: datetime) -> date:
	"""Recordings before noon belong to the previous evening's session."""
	return now.date() - timedelta(days=1) if now.hour < 12 else now.date()


def compute_window(now: datetime, start_hhmm: str, end_hhmm: str) -> SessionWindow:
	start_t = parse_hhmm(start_hhmm)
	end_t = parse_hhmm(end_hhmm)
	sd = session_date_for(now)
	starts_at = datetime.combine(sd, start_t)
	end_date = sd if end_t > start_t else sd + timedelta(days=1)
	ends_at = datetime.combine(end_date, end_t)
	return SessionWindow(session_date=sd, starts_at=starts_at, ends_at=ends_at)
