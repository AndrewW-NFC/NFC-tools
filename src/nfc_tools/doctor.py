"""Health checks. Plain-English errors, fixable suggestions."""

# Role: Provides installation and environment checks for the CLI and web interface.
# Dependencies: installer, config, ffmpeg_locator, and devices inspect local setup; HTTPX
# checks network access.
from __future__ import annotations
from dataclasses import dataclass

import httpx

from . import installer
from .config import load
from .ffmpeg_locator import find_ffmpeg
from .devices import list_input_devices, resolve_input_device


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
    try:
        device = resolve_input_device(cfg.recording.device, list_input_devices())
    except RuntimeError as exc:
        return Check("Microphone", False, str(exc), "Connect or choose an external microphone in Settings.")
    return Check("Microphone", True, f"Recording input: {device['name']}")


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
        detail = "Installed — included with NFC Tools; no separate installation needed." if s.get("builtin") else "Installed."
        return Check(f"Analyzer: {name}", True, detail)
    return Check(f"Analyzer: {name}", False, "Not installed yet.",
                 f"Click 'Install {name}' on the Settings page.")
