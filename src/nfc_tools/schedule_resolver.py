"""Resolve fixed or twilight-based recording schedules."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .ephemeris import preset_times
from .scheduler import SessionWindow, compute_window, normalize_evening_start, session_date_for

DEFAULT_TWILIGHT_PRESET = "civil"


@dataclass(frozen=True)
class ResolvedSchedule:
    session_date: date
    start_time: str
    end_time: str
    starts_at: datetime
    ends_at: datetime
    preset: str | None
    automatic: bool


def schedule_uses_twilight(cfg) -> bool:
    return getattr(cfg.schedule, "mode", "twilight") == "twilight" or bool(cfg.schedule.auto_apply_preset)


def schedule_times_for_date(cfg, session_date: date) -> tuple[str, str]:
    if schedule_uses_twilight(cfg):
        preset = cfg.schedule.preset or DEFAULT_TWILIGHT_PRESET
        try:
            return preset_times(
                preset,
                cfg.site.latitude,
                cfg.site.longitude,
                cfg.site.timezone,
                session_date,
            )
        except Exception:
            return cfg.schedule.start_time, cfg.schedule.end_time

    return cfg.schedule.start_time, cfg.schedule.end_time


def window_for_session_date(cfg, session_date: date) -> SessionWindow:
    start_time, end_time = schedule_times_for_date(cfg, session_date)
    zone = _site_zone(cfg.site.timezone)
    noon = datetime.combine(session_date, time(12), tzinfo=zone)
    timezone_name = cfg.site.timezone if zone else None
    return normalize_evening_start(compute_window(noon, start_time, end_time, timezone_name))


def next_window_for_config(cfg, now: datetime) -> SessionWindow:
    site_now = _datetime_for_site(now, cfg.site.timezone)
    base_date = session_date_for(site_now)

    for offset in range(3):
        candidate = window_for_session_date(cfg, base_date + timedelta(days=offset))
        comparison_now = _align_for_comparison(site_now, candidate.ends_at)
        if comparison_now < candidate.ends_at:
            return candidate

    return window_for_session_date(cfg, base_date + timedelta(days=3))


def current_schedule_preview(cfg, now: datetime | None = None) -> ResolvedSchedule:
    win = next_window_for_config(cfg, now or datetime.now())
    start_time, end_time = schedule_times_for_date(cfg, win.session_date)
    automatic = schedule_uses_twilight(cfg)
    return ResolvedSchedule(
        session_date=win.session_date,
        start_time=start_time,
        end_time=end_time,
        starts_at=win.starts_at,
        ends_at=win.ends_at,
        preset=(cfg.schedule.preset or DEFAULT_TWILIGHT_PRESET) if automatic else None,
        automatic=automatic,
    )


def _site_zone(timezone_name: str | None) -> ZoneInfo | None:
    if not timezone_name:
        return None
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return None


def _datetime_for_site(value: datetime, timezone_name: str | None) -> datetime:
    zone = _site_zone(timezone_name)
    if not zone:
        return value
    return value.astimezone(zone) if value.tzinfo else value.replace(tzinfo=zone)


def _align_for_comparison(value: datetime, target: datetime) -> datetime:
    if target.tzinfo and target.utcoffset() is not None:
        return value.astimezone(target.tzinfo) if value.tzinfo else value.replace(tzinfo=target.tzinfo)
    if value.tzinfo and value.utcoffset() is not None:
        return value.replace(tzinfo=None)
    return value
