"""Resolve BirdNET scientific names against a pinned eBird crosswalk.

Role: Keep uncertain taxonomy out of upload files while retaining review evidence.
Dependencies: Packaged CSV and manifest; no network or installed analyzer required.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

RESOURCE = "birdnet_ebird_crosswalk_v2026_1"


@dataclass(frozen=True)
class Mapping:
    status: str
    reason: str
    version: str
    common: str = ""
    scientific: str = ""
    code: str = ""


@lru_cache(maxsize=1)
def _crosswalk() -> tuple[str, dict[str, Mapping]]:
    root = resources.files("nfc_tools.data")
    manifest = json.loads(root.joinpath(RESOURCE + ".json").read_text(encoding="utf-8"))
    data = root.joinpath(RESOURCE + ".csv").read_bytes()
    if hashlib.sha256(data).hexdigest() != manifest["sha256"]:
        raise ValueError("BirdNET/eBird crosswalk checksum mismatch")
    version = manifest["version"]
    mappings = {}
    for row in csv.DictReader(io.StringIO(data.decode("utf-8"))):
        scientific = row["birdnet_scientific"]
        if scientific in mappings or row["status"] not in {"mapped", "review_required", "non_bird"}:
            raise ValueError("Invalid BirdNET/eBird crosswalk row")
        mappings[scientific] = Mapping(row["status"], row["reason"], version,
                                       row["ebird_common"], row["ebird_scientific"], row["ebird_code"])
    return version, mappings


def resolve(scientific: str) -> Mapping:
    """Never guess from common names or stale analyzer species codes."""
    version, mappings = _crosswalk()
    return mappings.get(scientific.strip(), Mapping("review_required", "unknown_scientific_name", version))
