"""Audio input device enumeration via ffmpeg."""
from __future__ import annotations
import platform
import re
import subprocess
from typing import List, Dict

from .ffmpeg_locator import ensure_ffmpeg
from .logging_setup import get

log = get("devices")


def list_input_devices() -> List[Dict]:
	system = platform.system()
	ffmpeg = ensure_ffmpeg()
	try:
		if system == "Darwin":
			return _list_avfoundation(ffmpeg)
		if system == "Linux":
			return _list_pulse_or_alsa(ffmpeg)
		if system == "Windows":
			return _list_dshow(ffmpeg)
	except Exception as e:  # noqa: BLE001
		log.error("device enumeration failed: %s", e)
	return []


def _run(cmd: list[str]) -> str:
	p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
	return p.stderr + p.stdout


def _list_avfoundation(ffmpeg: str) -> List[Dict]:
	out = _run([ffmpeg, "-hide_banner", "-f", "avfoundation",
				"-list_devices", "true", "-i", ""])
	devs = []
	in_audio = False
	for line in out.splitlines():
		if "AVFoundation audio devices" in line:
			in_audio = True
			continue
		if in_audio:
			m = re.search(r"\[(\d+)\]\s+(.+)$", line)
			if m:
				idx, name = m.group(1), m.group(2).strip()
				devs.append({
					"id": f"avfoundation:{idx}",
					"name": name,
					"ffmpeg_input": ["-f", "avfoundation", "-i", f":{idx}"],
				})
	return devs


def _list_pulse_or_alsa(ffmpeg: str) -> List[Dict]:
	devs: List[Dict] = []
	try:
		pa = subprocess.run(["pactl", "list", "short", "sources"],
							capture_output=True, text=True, timeout=5)
		for line in pa.stdout.splitlines():
			parts = line.split("\t")
			if len(parts) >= 2:
				name = parts[1]
				devs.append({
					"id": f"pulse:{name}",
					"name": name,
					"ffmpeg_input": ["-f", "pulse", "-i", name],
				})
	except FileNotFoundError:
		pass
	if not devs:
		devs.append({
			"id": "alsa:default",
			"name": "Default ALSA input",
			"ffmpeg_input": ["-f", "alsa", "-i", "default"],
		})
	return devs


def _list_dshow(ffmpeg: str) -> List[Dict]:
	out = _run([ffmpeg, "-hide_banner", "-f", "dshow",
				"-list_devices", "true", "-i", "dummy"])
	devs = []
	for line in out.splitlines():
		m = re.search(r'"([^"]+)"\s+\(audio\)', line)
		if m:
			name = m.group(1)
			devs.append({
				"id": f"dshow:{name}",
				"name": name,
				"ffmpeg_input": ["-f", "dshow", "-i", f"audio={name}"],
			})
	return devs
