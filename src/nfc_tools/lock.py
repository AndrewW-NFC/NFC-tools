"""Cross-platform serialization of analysis jobs via atomic mkdir."""
from __future__ import annotations
import os
import time
from pathlib import Path

from .logging_setup import get

log = get("lock")


class LockTimeout(Exception):
	pass


class FileLock:
	def __init__(self, path: Path, timeout: int = 3600, poll: float = 1.0):
		self.path = path
		self.timeout = timeout
		self.poll = poll

	def __enter__(self):
		waited = 0.0
		while True:
			try:
				self.path.mkdir(parents=False, exist_ok=False)
				(self.path / "pid").write_text(str(os.getpid()))
				return self
			except FileExistsError:
				if waited >= self.timeout:
					raise LockTimeout(f"Could not acquire lock at {self.path}")
				time.sleep(self.poll)
				waited += self.poll
				if int(waited) % 30 == 0:
					log.info("waiting for lock at %s", self.path)

	def __exit__(self, *exc):
		try:
			for child in self.path.iterdir():
				child.unlink()
			self.path.rmdir()
		except FileNotFoundError:
			pass
