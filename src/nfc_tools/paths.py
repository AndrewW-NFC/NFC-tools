"""Cross-platform paths for config, data, logs, and cache."""
from __future__ import annotations
from pathlib import Path
from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="nfc-tools", appauthor=False)


def config_dir() -> Path:
    p = Path(_dirs.user_config_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def data_dir() -> Path:
    """Where recordings, results, and managed analyzer envs live."""
    p = Path(_dirs.user_data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = Path(_dirs.user_log_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_dir() -> Path:
    p = Path(_dirs.user_cache_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def recordings_root() -> Path:
    """Return the folder that contains nightly recording folders.

    User-facing recordings/results should be easy to find, so each session is
    stored directly on the Desktop in a folder named with the session start date:

        ~/Desktop/2026-06-10/

    App config, cache, logs, and managed analyzer environments still use the
    normal application-support locations.
    """
    p = Path.home() / "Desktop"
    p.mkdir(parents=True, exist_ok=True)
    return p
def analyzers_root() -> Path:
    """Where managed analyzer environments are installed."""
    p = data_dir() / "analyzers"
    p.mkdir(parents=True, exist_ok=True)
    return p


def night_dir(session_date: str) -> Path:
    p = recordings_root() / session_date
    (p / "audio").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p
