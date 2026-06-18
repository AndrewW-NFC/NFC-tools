"""User-facing configuration, persisted as YAML.

Designed for humans first: short keys, comments via the YAML file,
sensible defaults so a fresh install runs without editing.
"""
from __future__ import annotations
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import yaml
from pydantic import BaseModel, Field, field_validator
from tzlocal import get_localzone_name

from .paths import config_dir

CONFIG_PATH = config_dir() / "config.yaml"


def normalize_timezone(value: str | None, fallback: str | None = None) -> str:
    for candidate in (value, fallback, get_localzone_name()):
        if not candidate:
            continue
        text = str(candidate).strip()
        try:
            ZoneInfo(text)
        except ZoneInfoNotFoundError:
            continue
        return text
    return "UTC"


class Site(BaseModel):
    name: str = "My site"
    latitude: float = 42.415
    longitude: float = -71.156
    timezone: str = Field(default_factory=get_localzone_name)

    @field_validator("timezone")
    @classmethod
    def _timezone(cls, v: str) -> str:
        return normalize_timezone(v)


class Schedule(BaseModel):
    """Recording schedule for a single night.

    start_time and end_time are local clock strings (HH:MM).
    end_time is interpreted as next-morning if it's earlier than start_time.
    """
    start_time: str = "21:00"
    end_time: str = "06:15"
    segment_minutes: int = 60
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
    format_preset: str = "auto_native"
    backend: str = "auto"
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 32
    filename_prefix: str = "NFC"


class Analyzers(BaseModel):
    enabled: list[str] = Field(default_factory=lambda: ["birdnet", "nighthawk"])
    birdnet_min_conf: float = 0.25


class Notifications(BaseModel):
    on_failure: bool = True
    on_session_end: bool = True


class Power(BaseModel):
    """Power-source policy for recording and analysis."""

    sleep_prevention: str = "recording_and_analysis"
    analysis_policy: str = "immediate"
    min_battery_percent_for_analysis: int = 30
    low_battery_warning_percent: int = 20
    critical_battery_percent: int = 10
    critical_battery_action: str = "stop_recording_defer_analysis"

    @field_validator("sleep_prevention")
    @classmethod
    def _sleep_prevention(cls, v: str) -> str:
        allowed = {"recording_and_analysis", "recording_only", "off"}
        if v not in allowed:
            raise ValueError(f"Invalid sleep prevention policy: {v}")
        return v

    @field_validator("analysis_policy")
    @classmethod
    def _analysis_policy(cls, v: str) -> str:
        allowed = {"immediate", "defer_on_battery", "defer_below_threshold"}
        if v not in allowed:
            raise ValueError(f"Invalid analysis power policy: {v}")
        return v

    @field_validator("critical_battery_action")
    @classmethod
    def _critical_battery_action(cls, v: str) -> str:
        allowed = {"continue", "defer_analysis", "stop_recording_defer_analysis"}
        if v not in allowed:
            raise ValueError(f"Invalid critical battery action: {v}")
        return v

    @field_validator("min_battery_percent_for_analysis", "low_battery_warning_percent", "critical_battery_percent")
    @classmethod
    def _percent(cls, v: int) -> int:
        if not (0 <= int(v) <= 100):
            raise ValueError("Battery percentages must be between 0 and 100")
        return int(v)


class Advanced(BaseModel):
    lock_timeout_seconds: int = 3600
    keep_awake: bool = True
    web_host: str = "127.0.0.1"
    web_port: int = 8765


class Config(BaseModel):
    site: Site = Field(default_factory=Site)
    schedule: Schedule = Field(default_factory=Schedule)
    recording: Recording = Field(default_factory=Recording)
    analyzers: Analyzers = Field(default_factory=Analyzers)
    notifications: Notifications = Field(default_factory=Notifications)
    power: Power = Field(default_factory=Power)
    advanced: Advanced = Field(default_factory=Advanced)
    first_run_complete: bool = False


def load() -> Config:
    if CONFIG_PATH.exists():
        data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        cfg = Config(**data)
        if cfg.recording.sample_rate == 22050:
            cfg.recording.sample_rate = 48000
            save(cfg)
        return cfg
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
