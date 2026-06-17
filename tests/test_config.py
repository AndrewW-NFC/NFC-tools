from nfc_tools.config import Config, Schedule, normalize_timezone


def test_defaults_are_valid():
	cfg = Config()
	assert 0 <= cfg.analyzers.birdnet_min_conf <= 1
	assert ":" in cfg.schedule.start_time
	assert cfg.recording.sample_rate > 0
	assert cfg.power.sleep_prevention == "recording_and_analysis"
	assert cfg.power.analysis_policy == "immediate"
	assert cfg.power.critical_battery_action == "stop_recording_defer_analysis"


def test_time_validation():
	import pytest
	from pydantic import ValidationError
	with pytest.raises(ValidationError):
		Schedule(start_time="25:00", end_time="06:00")


def test_timezone_normalization_uses_valid_fallback():
	assert normalize_timezone("Invalid/Timezone", "America/New_York") == "America/New_York"
