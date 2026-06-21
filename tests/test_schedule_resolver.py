from datetime import datetime

from nfc_tools.config import Config
from nfc_tools.schedule_resolver import next_window_for_config, schedule_times_for_date


def test_automatic_twilight_schedule_uses_date_specific_times():
	cfg = Config()
	cfg.site.latitude = 42.414586
	cfg.site.longitude = -71.1728754
	cfg.site.timezone = "America/New_York"
	cfg.schedule.mode = "twilight"
	cfg.schedule.auto_apply_preset = True
	cfg.schedule.preset = "astronomical"
	cfg.schedule.start_time = "20:50"
	cfg.schedule.end_time = "04:37"

	win = next_window_for_config(cfg, datetime(2026, 6, 19, 12, 0))

	assert win.starts_at.strftime("%H:%M") == "22:39"
	assert win.ends_at.strftime("%H:%M") == "02:52"
	assert win.starts_at.strftime("%H:%M") != cfg.schedule.start_time
	assert win.ends_at.strftime("%H:%M") != cfg.schedule.end_time


def test_manual_schedule_keeps_saved_clock_times():
	cfg = Config()
	cfg.site.timezone = "America/New_York"
	cfg.schedule.mode = "manual"
	cfg.schedule.auto_apply_preset = False
	cfg.schedule.preset = None
	cfg.schedule.start_time = "20:50"
	cfg.schedule.end_time = "04:37"

	win = next_window_for_config(cfg, datetime(2026, 6, 19, 12, 0))

	assert win.starts_at.strftime("%H:%M") == "20:50"
	assert win.ends_at.strftime("%H:%M") == "04:37"


def test_twilight_schedule_changes_by_session_date():
	cfg = Config()
	cfg.site.latitude = 42.414586
	cfg.site.longitude = -71.1728754
	cfg.site.timezone = "America/New_York"
	cfg.schedule.mode = "twilight"
	cfg.schedule.auto_apply_preset = True
	cfg.schedule.preset = "astronomical"

	june_19 = schedule_times_for_date(cfg, datetime(2026, 6, 19).date())
	june_25 = schedule_times_for_date(cfg, datetime(2026, 6, 25).date())

	assert june_19 != june_25
