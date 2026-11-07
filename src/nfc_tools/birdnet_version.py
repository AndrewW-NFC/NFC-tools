"""Prevent upgrades from mixing analyzer versions in an existing analysis."""

# Role: Guards saved analysis against incompatible BirdNET upgrades.
# Dependencies: installer identifies the installed analyzer; JSON files retain its
# identity.
from __future__ import annotations

import json
from pathlib import Path

from .installer import BIRDNET_REQUIREMENT, BIRDNET3_LIBRARY_REQUIREMENT


def identity() -> dict:
    return {"analyzer": BIRDNET_REQUIREMENT, "library": BIRDNET3_LIBRARY_REQUIREMENT,
            "model": "3.0", "release": "preview3.1"}


def require_current(saved) -> None:
    if saved != identity():
        raise ValueError(
            "This analysis was started with a different or unrecorded BirdNET version. "
            "To keep the old results intact, start a new import in a fresh output folder, "
            "or finish this analysis with the previous NFC Tools app."
        )


def check_night(nd: Path, progress: dict) -> None:
    """Called while holding the night lock, before reusing or writing results."""
    known = set()
    for filename, entry in progress.get("files", {}).items():
        stage = entry.get("analyzers", {}).get("birdnet", {})
        if stage.get("analysis") in {"ok", "running", "failed", "error"}:
            require_current(stage.get("birdnet_version"))
            known.add(Path(filename).stem)
    # Older results can exist without a checkpoint (including legacy imports).
    root = nd / "results" / "birdnet"
    for folder in root.iterdir() if root.exists() else []:
        if folder.name in known:
            continue
        if not folder.is_dir():
            require_current(None)
        if not any(folder.iterdir()):
            continue
        policy = folder / "nfc_birdnet_policy.json"
        saved = json.loads(policy.read_text()) if policy.exists() else {}
        require_current({"analyzer": saved.get("analyzer_requirement"),
                         "library": "birdnet==" + str(saved.get("birdnet_library")),
                         "model": saved.get("model"), "release": saved.get("model_release")})
