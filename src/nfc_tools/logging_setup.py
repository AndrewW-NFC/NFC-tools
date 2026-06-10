"""Structured logging with severity tags. Logs go to a rotating file
in the user logs dir; the web UI reads recent entries from there."""
from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path

from .paths import logs_dir

_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE = "%Y-%m-%d %H:%M:%S"


def setup(level: str = "INFO") -> Path:
	log_path = logs_dir() / "nfc.log"
	handler = logging.handlers.RotatingFileHandler(
		log_path, maxBytes=5_000_000, backupCount=5
	)
	handler.setFormatter(logging.Formatter(_FMT, _DATE))

	stream = logging.StreamHandler()
	stream.setFormatter(logging.Formatter(_FMT, _DATE))

	root = logging.getLogger()
	root.setLevel(level)
	root.handlers = [handler, stream]
	return log_path


def get(name: str) -> logging.Logger:
	return logging.getLogger(f"nfc.{name}")
