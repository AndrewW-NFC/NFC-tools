from datetime import datetime

from nfc_tools.segments import seconds_until_next_segment_boundary, segment_period_for_start


def test_segment_period_names_follow_nfc_window():
	nfc_start = datetime(2026, 5, 10, 21, 57)
	nfc_end = datetime(2026, 5, 11, 4, 18)

	assert segment_period_for_start(datetime(2026, 5, 10, 20, 30), nfc_start, nfc_end) == "pre"
	assert segment_period_for_start(datetime(2026, 5, 10, 21, 57), nfc_start, nfc_end) == "nfc"
	assert segment_period_for_start(datetime(2026, 5, 11, 4, 18), nfc_start, nfc_end) == "post"


def test_segment_length_stops_at_astronomical_boundaries():
	nfc_start = datetime(2026, 5, 10, 21, 57)
	nfc_end = datetime(2026, 5, 11, 4, 18)

	assert seconds_until_next_segment_boundary(datetime(2026, 5, 10, 21, 30), 3600, nfc_start, nfc_end) == 27 * 60
	assert seconds_until_next_segment_boundary(datetime(2026, 5, 10, 22, 0), 3600, nfc_start, nfc_end) == 3600
	assert seconds_until_next_segment_boundary(datetime(2026, 5, 11, 3, 45), 3600, nfc_start, nfc_end) == 33 * 60
