"""Cross-platform paths for config, data, logs, and cache."""

# Role: Centralizes user storage locations and development-profile separation.
# Dependencies: platformdirs chooses OS conventions; environment variables and pathlib
# resolve overrides.
from __future__ import annotations
import os
from pathlib import Path
from platformdirs import PlatformDirs

IS_DEV = os.environ.get("NFC_TOOLS_PROFILE") == "dev"
_dirs = PlatformDirs(appname="nfc-tools-dev" if IS_DEV else "nfc-tools", appauthor=False)


def dev_output_root() -> Path:
    return Path.home() / "Desktop" / "nfc-tools-dev-output"


def validate_output_root(path: Path) -> Path:
    if IS_DEV:
        base = dev_output_root().resolve()
        resolved = path.expanduser().resolve()
        if resolved != base and base not in resolved.parents:
            raise ValueError(f"Development results must stay inside {base}")
    return path



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


def recordings_root_path(save_location: str | None = None) -> Path:
    root = (save_location or "").strip()
    return validate_output_root(Path(root).expanduser() if root else (dev_output_root() if IS_DEV else Path.home() / "Desktop"))


def recordings_root(save_location: str | None = None) -> Path:
    """Return the folder that contains nightly recording folders.

    User-facing recordings/results should be easy to find, so each session is
    stored in a folder named with the session start date:

        <recordings root>/2026-06-10/

    The default root remains the Desktop. Users can choose a different root,
    such as an external drive, from Settings.
    """
    p = recordings_root_path(save_location)
    p.mkdir(parents=True, exist_ok=True)
    return p


def analyzers_root() -> Path:
    """Where managed analyzer environments are installed."""
    p = data_dir() / "analyzers"
    p.mkdir(parents=True, exist_ok=True)
    return p


def night_dir(session_date: str, save_location: str | None = None) -> Path:
    p = recordings_root(save_location) / session_date
    (p / "audio").mkdir(parents=True, exist_ok=True)
    (p / "results").mkdir(parents=True, exist_ok=True)
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p
