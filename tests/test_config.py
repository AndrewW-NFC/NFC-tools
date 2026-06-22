import nfc_tools.config as config_mod
from nfc_tools.config import Config, Schedule, normalize_timezone


def test_defaults_are_valid():
	cfg = Config()
	assert 0 <= cfg.analyzers.birdnet_min_conf <= 1
	assert ":" in cfg.schedule.start_time
	assert cfg.recording.sample_rate > 0
	assert cfg.recording.save_location == ""
	assert cfg.site.timezone == "America/New_York"
	assert cfg.schedule.mode == "twilight"
	assert cfg.schedule.preset == "civil"
	assert cfg.schedule.auto_apply_preset is True
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


def test_load_ignores_removed_fields_and_migrates_old_sample_rate(tmp_path, monkeypatch):
	config_path = tmp_path / "config.yaml"
	config_path.write_text(
		"""
schedule:
  start_time: "21:00"
  end_time: "06:15"
  pause_seconds: 5
recording:
  sample_rate: 22050
analyzers:
  parallel: true
autoschedule:
  enabled: true
output_root: /tmp/old-output
first_run_complete: false
""",
		encoding="utf-8",
	)
	monkeypatch.setattr(config_mod, "CONFIG_PATH", config_path)

	cfg = config_mod.load()

	assert cfg.recording.sample_rate == 48000
	assert not hasattr(cfg.schedule, "pause_seconds")
	assert not hasattr(cfg.analyzers, "parallel")
	assert not hasattr(cfg, "autoschedule")
	assert not hasattr(cfg, "output_root")
	assert not hasattr(cfg, "first_run_complete")


def test_load_migrates_automatic_evening_only_default_to_civil(tmp_path, monkeypatch):
	config_path = tmp_path / "config.yaml"
	config_path.write_text(
		"""
schedule:
  mode: twilight
  start_time: "20:24"
  end_time: "23:59"
  preset: evening-only
  auto_apply_preset: true
""",
		encoding="utf-8",
	)
	monkeypatch.setattr(config_mod, "CONFIG_PATH", config_path)

	cfg = config_mod.load()

	assert cfg.schedule.preset == "civil"
	assert "preset: civil" in config_path.read_text(encoding="utf-8")


def test_load_migrates_default_site_away_from_utc(tmp_path, monkeypatch):
	config_path = tmp_path / "config.yaml"
	config_path.write_text(
		"""
site:
  name: My site
  latitude: 42.415
  longitude: -71.156
  timezone: Etc/UTC
""",
		encoding="utf-8",
	)
	monkeypatch.setattr(config_mod, "CONFIG_PATH", config_path)

	cfg = config_mod.load()

	assert cfg.site.timezone == "America/New_York"
	assert "timezone: America/New_York" in config_path.read_text(encoding="utf-8")
