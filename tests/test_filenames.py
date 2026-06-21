from datetime import date, datetime
from nfc_tools.filenames import parse, make, next_index_for_directory


def test_current_format():
	p = parse("001_NFC_2026-05-11_03-22-14.wav")
	assert p is not None
	assert p.session_date == date(2026, 5, 10)
	assert p.recorded_at == datetime(2026, 5, 11, 3, 22, 14)
	assert p.is_legacy is False
	assert p.index == 1


def test_unindexed_current_format_still_parses():
	p = parse("NFC_2026-05-11_03-22-14.wav")
	assert p is not None
	assert p.session_date == date(2026, 5, 10)
	assert p.recorded_at == datetime(2026, 5, 11, 3, 22, 14)
	assert p.is_legacy is False
	assert p.index is None


def test_session_dated_format_still_parses():
	p = parse("002_NFC_2026-05-10_2026-05-11_03-22-14.wav")
	assert p is not None
	assert p.session_date == date(2026, 5, 10)
	assert p.recorded_at == datetime(2026, 5, 11, 3, 22, 14)
	assert p.is_legacy is False
	assert p.index == 2


def test_legacy_am_belongs_to_previous_evening():
	p = parse("NFCs starting 2026-05-11 03-22-14.wav")
	assert p is not None
	assert p.session_date == date(2026, 5, 10)
	assert p.is_legacy is True


def test_legacy_pm_same_day():
	p = parse("NFCs starting 2026-05-10 22-15-03.wav")
	assert p.session_date == date(2026, 5, 10)


def test_make_roundtrip():
	fn = make("NFC", date(2026, 5, 10), datetime(2026, 5, 11, 3, 22, 14), index=1)
	assert fn == "001_NFC_2026-05-11_03-22-14.wav"
	p = parse(fn)
	assert p.session_date == date(2026, 5, 10)
	assert p.recorded_at == datetime(2026, 5, 11, 3, 22, 14)
	assert p.period == "nfc"
	assert p.index == 1


def test_make_keeps_unindexed_compatibility():
	fn = make("NFC", date(2026, 5, 10), datetime(2026, 5, 11, 3, 22, 14))
	assert fn == "NFC_2026-05-11_03-22-14.wav"


def test_make_rejects_non_positive_index():
	try:
		make("NFC", date(2026, 5, 10), datetime(2026, 5, 11, 3, 22, 14), index=0)
	except ValueError:
		pass
	else:
		raise AssertionError("Expected ValueError")


def test_make_civil_period_names():
	evening = make("NFC", date(2026, 5, 10), datetime(2026, 5, 10, 20, 27, 0), period="civil_evening", index=1)
	morning = make("NFC", date(2026, 5, 10), datetime(2026, 5, 11, 4, 49, 0), period="civil_morning", index=3)

	assert evening == "001_NFC_CIVIL_EVENING_2026-05-10_20-27-00.wav"
	assert morning == "003_NFC_CIVIL_MORNING_2026-05-11_04-49-00.wav"
	assert parse(evening).period == "civil_evening"
	assert parse(morning).period == "civil_morning"
	assert parse(morning).session_date == date(2026, 5, 10)


def test_unknown_returns_none():
	assert parse("random.wav") is None


def test_next_index_for_directory_counts_existing_recordings(tmp_path):
	(tmp_path / "001_NFC_2026-05-10_21-00-00.wav").write_bytes(b"RIFF")
	(tmp_path / "002_NFC_2026-05-10_22-00-00.WAV").write_bytes(b"RIFF")

	assert next_index_for_directory(tmp_path) == 3


def test_next_index_for_directory_counts_unindexed_recordings(tmp_path):
	(tmp_path / "NFC_CIVIL_EVENING_2026-05-10_20-27-00.wav").write_bytes(b"RIFF")
	(tmp_path / "NFC_2026-05-10_21-00-00.wav").write_bytes(b"RIFF")

	assert next_index_for_directory(tmp_path) == 3
