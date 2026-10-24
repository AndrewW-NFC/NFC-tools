from datetime import datetime
from zoneinfo import ZoneInfo

from nfc_tools.segments import seconds_until_next_segment_boundary, segment_period_for_start


def test_segment_period_names_follow_nfc_window():
	nfc_start = datetime(2026, 5, 10, 21, 57)
	nfc_end = datetime(2026, 5, 11, 4, 18)

	assert segment_period_for_start(datetime(2026, 5, 10, 20, 30), nfc_start, nfc_end) == "civil_evening"
	assert segment_period_for_start(datetime(2026, 5, 10, 21, 57), nfc_start, nfc_end) == "nfc"
	assert segment_period_for_start(datetime(2026, 5, 11, 4, 18), nfc_start, nfc_end) == "civil_morning"


def test_segment_length_stops_at_astronomical_boundaries():
	nfc_start = datetime(2026, 5, 10, 21, 57)
	nfc_end = datetime(2026, 5, 11, 4, 18)

	assert seconds_until_next_segment_boundary(datetime(2026, 5, 10, 21, 30), 3600, nfc_start, nfc_end) == 27 * 60
	assert seconds_until_next_segment_boundary(datetime(2026, 5, 10, 22, 0), 3600, nfc_start, nfc_end) == 3600
	assert seconds_until_next_segment_boundary(datetime(2026, 5, 11, 3, 45), 3600, nfc_start, nfc_end) == 33 * 60


def test_segment_length_stops_at_midnight():
	nfc_start = datetime(2026, 5, 10, 21, 57)
	nfc_end = datetime(2026, 5, 11, 4, 18)

	assert seconds_until_next_segment_boundary(datetime(2026, 5, 10, 23, 39), 3600, nfc_start, nfc_end) == 21 * 60


def test_segment_length_stops_at_civil_boundaries():
	civil_start = datetime(2026, 5, 10, 20, 55)
	nfc_start = datetime(2026, 5, 10, 21, 57)
	nfc_end = datetime(2026, 5, 11, 4, 18)
	civil_end = datetime(2026, 5, 11, 5, 4)

	assert seconds_until_next_segment_boundary(
		datetime(2026, 5, 10, 20, 30),
		3600,
		nfc_start,
		nfc_end,
		civil_start,
		civil_end,
	) == 25 * 60
	assert seconds_until_next_segment_boundary(
		datetime(2026, 5, 11, 4, 45),
		3600,
		nfc_start,
		nfc_end,
		civil_start,
		civil_end,
	) == 19 * 60


def test_segment_period_snaps_near_twilight_boundaries():
	nfc_start = datetime(2026, 6, 17, 22, 39, 0, 500000)
	nfc_end = datetime(2026, 6, 18, 2, 52, 11, 500000)

	assert segment_period_for_start(datetime(2026, 6, 17, 22, 38, 59, 800000), nfc_start, nfc_end) == "nfc"
	assert segment_period_for_start(datetime(2026, 6, 18, 2, 52, 10, 800000), nfc_start, nfc_end) == "civil_morning"


def test_segment_helpers_accept_timezone_aware_nfc_boundaries():
	zone = ZoneInfo("America/New_York")
	nfc_start = datetime(2026, 6, 16, 22, 38, tzinfo=zone)
	nfc_end = datetime(2026, 6, 17, 2, 52, tzinfo=zone)

	assert segment_period_for_start(datetime(2026, 6, 16, 20, 54), nfc_start, nfc_end) == "civil_evening"
	assert seconds_until_next_segment_boundary(datetime(2026, 6, 16, 21, 54), 3600, nfc_start, nfc_end) == 44 * 60


def test_daily_periods_and_boundaries_follow_each_recording_date():
    from datetime import date, timedelta
    from nfc_tools.config import Config
    from nfc_tools.ephemeris import sun_times
    from nfc_tools.segments import recording_period_and_seconds
    site = Config().site
    site.latitude, site.longitude, site.timezone = 42, -71, 'America/New_York'
    for day in [date(2026, 10, 24), date(2026, 10, 25), date(2026, 11, 1)]:
        sun = sun_times(day, 42, -71, site.timezone)
        boundaries = [(sun.astronomical_dawn, 'civil_morning'),
                      (sun.civil_dawn, 'morning_flight'),
                      (sun.sunrise + timedelta(hours=2), 'daytime'),
                      (sun.civil_dusk, 'civil_evening'),
                      (sun.astronomical_dusk, 'nfc')]
        for boundary, expected in boundaries:
            assert recording_period_and_seconds(boundary, 3600, site)[0] == expected
            assert recording_period_and_seconds(boundary - timedelta(minutes=5), 3600, site)[1] == 300
