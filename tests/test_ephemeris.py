from datetime import date
from nfc_tools.ephemeris import sun_times, preset_times


def test_sun_times_in_known_window():
	s = sun_times(date(2026, 5, 15), 42.36, -71.06, "America/New_York")
	assert 4 <= s.sunrise.hour <= 7
	assert 18 <= s.sunset.hour <= 21


def test_civil_preset_returns_hhmm():
	start, end = preset_times("civil", 42.36, -71.06, "America/New_York", date(2026, 5, 15))
	assert ":" in start and ":" in end
	h, m = (int(x) for x in start.split(":"))
	assert 0 <= h < 24 and 0 <= m < 60


def test_unknown_preset_raises():
	import pytest
	with pytest.raises(ValueError):
		preset_times("nope", 0, 0, "UTC")
