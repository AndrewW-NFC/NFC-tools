"""Locate or auto-install ffmpeg.

Strategy:
  1. Use bundled ffmpeg if present (alongside the .app).
  2. Use system ffmpeg if on PATH.
  3. Use imageio-ffmpeg if installed.
  4. Otherwise, prompt the installer to fetch a static build.
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path
from typing import Optional


def find_ffmpeg() -> Optional[str]:
	exe_dir = Path(sys.executable).resolve().parent
	for name in ("ffmpeg", "ffmpeg.exe"):
		candidate = exe_dir / name
		if candidate.exists():
			return str(candidate)
		candidate = exe_dir.parent / "Resources" / name
		if candidate.exists():
			return str(candidate)
	found = shutil.which("ffmpeg")
	if found:
		return found
	try:
		import imageio_ffmpeg  # type: ignore
		return imageio_ffmpeg.get_ffmpeg_exe()
	except Exception:  # noqa: BLE001
		pass
	return None


def ensure_ffmpeg() -> str:
	path = find_ffmpeg()
	if path:
		return path
	from .installer import install_ffmpeg
	return install_ffmpeg()
