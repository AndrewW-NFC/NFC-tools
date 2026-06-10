"""Cross-platform desktop notifications. Falls back to logging."""
from __future__ import annotations
import platform
import shutil
import subprocess

from .logging_setup import get

log = get("notify")


def notify(title: str, message: str) -> None:
	system = platform.system()
	try:
		if system == "Darwin" and shutil.which("osascript"):
			script = f'display notification "{message}" with title "{title}"'
			subprocess.run(["osascript", "-e", script], check=False, timeout=5)
			return
		if system == "Linux" and shutil.which("notify-send"):
			subprocess.run(["notify-send", title, message], check=False, timeout=5)
			return
		if system == "Windows":
			try:
				from winotify import Notification  # type: ignore
				Notification(app_id="NFC Tools", title=title, msg=message).show()
				return
			except ImportError:
				pass
	except Exception as e:  # noqa: BLE001
		log.debug("notification failed: %s", e)
	log.info("[notify] %s — %s", title, message)
