from datetime import datetime, date
from nfc_tools.scheduler import compute_window, session_date_for


def test_session_date_evening():
	assert session_date_for(datetime(2026, 5, 10, 21, 0)) == date(2026, 5, 10)


def test_session_date_morning_belongs_to_yesterday():
	assert session_date_for(datetime(2026, 5, 11, 3, 0)) == date(2026, 5, 10)


def test_window_crosses_midnight():
	w = compute_window(datetime(2026, 5, 10, 21, 0), "21:00", "06:15")
	assert w.session_date == date(2026, 5, 10)
	assert w.starts_at == datetime(2026, 5, 10, 21, 0)
	assert w.ends_at == datetime(2026, 5, 11, 6, 15)
	assert w.crosses_midnight


def test_window_same_day():
	w = compute_window(datetime(2026, 5, 10, 13, 0), "13:00", "17:00")
	assert not w.crosses_midnight
