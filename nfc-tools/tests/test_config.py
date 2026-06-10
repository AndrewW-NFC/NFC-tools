from nfc_tools.config import Config, Schedule


def test_defaults_are_valid():
	cfg = Config()
	assert 0 <= cfg.analyzers.birdnet_min_conf <= 1
	assert ":" in cfg.schedule.start_time
	assert cfg.recording.sample_rate > 0


def test_time_validation():
	import pytest
	from pydantic import ValidationError
	with pytest.raises(ValidationError):
		Schedule(start_time="25:00", end_time="06:00")
