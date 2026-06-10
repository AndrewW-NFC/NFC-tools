"""Health checks. Plain-English errors, fixable suggestions."""
from __future__ import annotations
from dataclasses import dataclass

import httpx

from . import installer
from .config import load
from .ffmpeg_locator import find_ffmpeg
from .devices import list_input_devices


@dataclass
class Check:
	name: str
	ok: bool
	detail: str
	fix_hint: str = ""


def run_all() -> list[Check]:
	cfg = load()
	out: list[Check] = []

	out.append(_check_ffmpeg())
	out.append(_check_devices(cfg))
	out.append(_check_network())
	for name in cfg.analyzers.enabled:
		out.append(_check_analyzer(name))
	return out


def _check_ffmpeg() -> Check:
	p = find_ffmpeg()
	if p:
		return Check("Audio engine (ffmpeg)", True, f"Found at {p}")
	return Check(
		"Audio engine (ffmpeg)", False,
		"ffmpeg not found.",
		"Click 'Install audio engine' on the Settings page, or install ffmpeg manually."
	)


def _check_devices(cfg) -> Check:
	devs = list_input_devices()
	if not devs:
		return Check("Microphone", False, "No audio input devices detected.",
					 "Connect a mic and click 'Refresh devices'.")
	if cfg.recording.device:
		if any(d["id"] == cfg.recording.device for d in devs):
			return Check("Microphone", True, f"Configured device available: {cfg.recording.device}")
		return Check("Microphone", False,
					 f"Configured device not found: {cfg.recording.device}",
					 "Choose a different mic on the Settings page.")
	return Check("Microphone", True, f"{len(devs)} device(s) detected; not yet selected.",
				 "Pick a mic in Settings.")


def _check_network() -> Check:
	try:
		httpx.get("https://api.open-meteo.com/v1/forecast",
				  params={"latitude": 0, "longitude": 0, "current_weather": True},
				  timeout=5).raise_for_status()
		return Check("Internet (weather)", True, "Open-Meteo reachable.")
	except Exception:  # noqa: BLE001
		return Check("Internet (weather)", False,
					 "Couldn't reach the weather service.",
					 "Recording still works, but weather logs will be empty.")


def _check_analyzer(name: str) -> Check:
	s = installer.status().get(name, {"installed": False})
	if s["installed"]:
		return Check(f"Analyzer: {name}", True, "Installed.")
	return Check(f"Analyzer: {name}", False, "Not installed yet.",
				 f"Click 'Install {name}' on the Settings page.")
