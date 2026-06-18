from datetime import date, timedelta
from nfc_tools.ephemeris import astronomical_nfc_window, civil_recording_window, sun_times, preset_times


def test_sun_times_in_known_window():
	s = sun_times(date(2026, 5, 15), 42.36, -71.06, "America/New_York")
	assert s.sunrise.date() == date(2026, 5, 15)
	assert s.sunset.date() == date(2026, 5, 15)
	assert s.astronomical_dawn.date() == date(2026, 5, 15)
	assert s.astronomical_dusk.date() == date(2026, 5, 15)
	assert 4 <= s.sunrise.hour <= 7
	assert 18 <= s.sunset.hour <= 21
	assert s.astronomical_dawn < s.civil_dawn < s.sunrise
	assert s.sunset < s.civil_dusk < s.astronomical_dusk


def test_civil_preset_returns_hhmm():
	start, end = preset_times("civil", 42.36, -71.06, "America/New_York", date(2026, 5, 15))
	assert ":" in start and ":" in end
	h, m = (int(x) for x in start.split(":"))
	assert 0 <= h < 24 and 0 <= m < 60


def test_astronomical_helpers_use_sun_altitude_twilight():
	d = date(2026, 5, 15)
	nfc_start, nfc_end = astronomical_nfc_window(d, 42.36, -71.06, "America/New_York")
	recording_start, recording_end = civil_recording_window(d, 42.36, -71.06, "America/New_York")
	today = sun_times(d, 42.36, -71.06, "America/New_York")
	tomorrow = sun_times(date(2026, 5, 16), 42.36, -71.06, "America/New_York")

	assert nfc_start.date() == d
	assert nfc_end.date() == date(2026, 5, 16)
	assert nfc_start == today.astronomical_dusk
	assert nfc_end == tomorrow.astronomical_dawn
	assert recording_start == today.civil_dusk
	assert recording_end == tomorrow.civil_dawn
	assert recording_start < nfc_start
	assert nfc_end < recording_end
	assert nfc_start.strftime("%H:%M") != (today.sunset + timedelta(minutes=90)).strftime("%H:%M")


def test_astronomical_preset_returns_civil_recording_window():
	d = date(2026, 5, 15)
	start, end = preset_times("astronomical", 42.36, -71.06, "America/New_York", d)
	recording_start, recording_end = civil_recording_window(d, 42.36, -71.06, "America/New_York")

	assert start == recording_start.strftime("%H:%M")
	assert end == recording_end.strftime("%H:%M")


def test_unknown_preset_raises():
	import pytest
	with pytest.raises(ValueError):
		preset_times("nope", 0, 0, "UTC")
