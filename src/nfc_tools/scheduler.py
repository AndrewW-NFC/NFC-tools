"""Compute session timing windows. Pure functions; easy to test."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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


def compute_window(now: datetime, start_hhmm: str, end_hhmm: str, timezone_name: str | None = None) -> SessionWindow:
    start_t = parse_hhmm(start_hhmm)
    end_t = parse_hhmm(end_hhmm)
    if timezone_name:
        try:
            zone = ZoneInfo(timezone_name)
            now = now.astimezone(zone) if now.tzinfo else now.replace(tzinfo=zone)
        except ZoneInfoNotFoundError:
            zone = now.tzinfo
    else:
        zone = now.tzinfo
    sd = session_date_for(now)
    starts_at = datetime.combine(sd, start_t, tzinfo=zone)
    end_date = sd if end_t > start_t else sd + timedelta(days=1)
    ends_at = datetime.combine(end_date, end_t, tzinfo=zone)
    return SessionWindow(session_date=sd, starts_at=starts_at, ends_at=ends_at)


def normalize_evening_start(win: SessionWindow) -> SessionWindow:
    """Treat morning-looking dusk starts as PM for overnight NFC sessions.

    Twilight presets are persisted as local HH:MM strings. Around some dates and
    sites, the computed start string can look like a morning time even though it
    refers to the evening half of an overnight recording window.
    """
    if (
        win.starts_at.hour < 12
        and win.ends_at.date() > win.starts_at.date()
        and win.ends_at.hour < 12
    ):
        return SessionWindow(
            session_date=win.session_date,
            starts_at=win.starts_at + timedelta(hours=12),
            ends_at=win.ends_at,
        )
    return win


def next_relevant_window(
    now: datetime,
    start_hhmm: str,
    end_hhmm: str,
    timezone_name: str | None = None,
) -> SessionWindow:
    """Return the active or next overnight window for dashboard/session starts."""
    win = normalize_evening_start(compute_window(now, start_hhmm, end_hhmm, timezone_name))
    comparison_now = now
    if win.ends_at.tzinfo and win.ends_at.utcoffset() is not None:
        comparison_now = (
            now.astimezone(win.ends_at.tzinfo)
            if now.tzinfo
            else now.replace(tzinfo=win.ends_at.tzinfo)
        )
    elif now.tzinfo and now.utcoffset() is not None:
        comparison_now = now.replace(tzinfo=None)
    if comparison_now >= win.ends_at:
        win = normalize_evening_start(
            compute_window(comparison_now + timedelta(hours=12), start_hhmm, end_hhmm, timezone_name)
        )
    return win
