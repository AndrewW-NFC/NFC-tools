from datetime import date, datetime
from nfc_tools.filenames import parse, make


def test_current_format():
	p = parse("NFC_2026-05-10_2026-05-11_03-22-14.wav")
	assert p is not None
	assert p.session_date == date(2026, 5, 10)
	assert p.recorded_at == datetime(2026, 5, 11, 3, 22, 14)
	assert p.is_legacy is False


def test_legacy_am_belongs_to_previous_evening():
	p = parse("NFCs starting 2026-05-11 03-22-14.wav")
	assert p is not None
	assert p.session_date == date(2026, 5, 10)
	assert p.is_legacy is True


def test_legacy_pm_same_day():
	p = parse("NFCs starting 2026-05-10 22-15-03.wav")
	assert p.session_date == date(2026, 5, 10)


def test_make_roundtrip():
	fn = make("NFC", date(2026, 5, 10), datetime(2026, 5, 11, 3, 22, 14))
	p = parse(fn)
	assert p.session_date == date(2026, 5, 10)
	assert p.recorded_at == datetime(2026, 5, 11, 3, 22, 14)


def test_unknown_returns_none():
	assert parse("random.wav") is None
