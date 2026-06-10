"""User-facing configuration, persisted as YAML.

Designed for humans first: short keys, comments via the YAML file,
sensible defaults so a fresh install runs without editing.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import yaml
from pydantic import BaseModel, Field, field_validator
from tzlocal import get_localzone_name

from .paths import config_dir, recordings_root

CONFIG_PATH = config_dir() / "config.yaml"


class Site(BaseModel):
	name: str = "My site"
	latitude: float = 42.415
	longitude: float = -71.156
	timezone: str = Field(default_factory=get_localzone_name)


class Schedule(BaseModel):
	"""Recording schedule for a single night.

	start_time and end_time are local clock strings (HH:MM).
	end_time is interpreted as next-morning if it's earlier than start_time.
	"""
	start_time: str = "21:00"
	end_time: str = "06:15"
	segment_minutes: int = 60
	pause_seconds: int = 5
	preset: Optional[str] = None
	auto_apply_preset: bool = False

	@field_validator("start_time", "end_time")
	@classmethod
	def _hhmm(cls, v: str) -> str:
		h, m = v.split(":")
		if not (0 <= int(h) < 24 and 0 <= int(m) < 60):
			raise ValueError(f"Invalid time: {v}")
		return f"{int(h):02d}:{int(m):02d}"


class Recording(BaseModel):
	device: Optional[str] = None
	sample_rate: int = 22050
	channels: int = 1
	bit_depth: int = 16
	filename_prefix: str = "NFC"


class Analyzers(BaseModel):
	enabled: list[str] = Field(default_factory=lambda: ["birdnet", "nighthawk"])
	birdnet_min_conf: float = 0.25
	parallel: bool = True


class Notifications(BaseModel):
	on_failure: bool = True
	on_session_end: bool = True


class Advanced(BaseModel):
	lock_timeout_seconds: int = 3600
	keep_awake: bool = True
	web_host: str = "127.0.0.1"
	web_port: int = 8765


class Autoschedule(BaseModel):
	enabled: bool = False


class Config(BaseModel):
	site: Site = Field(default_factory=Site)
	schedule: Schedule = Field(default_factory=Schedule)
	recording: Recording = Field(default_factory=Recording)
	analyzers: Analyzers = Field(default_factory=Analyzers)
	notifications: Notifications = Field(default_factory=Notifications)
	advanced: Advanced = Field(default_factory=Advanced)
	autoschedule: Autoschedule = Field(default_factory=Autoschedule)
	first_run_complete: bool = False
	output_root: str = Field(default_factory=lambda: str(recordings_root()))


def load() -> Config:
	if CONFIG_PATH.exists():
		data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
		return Config(**data)
	cfg = Config()
	save(cfg)
	return cfg


def save(cfg: Config) -> None:
	CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
	CONFIG_PATH.write_text(_yaml_with_comments(cfg))


def _yaml_with_comments(cfg: Config) -> str:
	header = (
		"# NFC Tools configuration\n"
		"# Most settings are managed by the app's Settings page.\n"
		"# You can edit this file directly, but the app must be stopped first.\n\n"
	)
	body = yaml.safe_dump(cfg.model_dump(), sort_keys=False, default_flow_style=False)
	return header + body
