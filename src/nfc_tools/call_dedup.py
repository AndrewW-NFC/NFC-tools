"""Automatic timestamp grouping; estimates events, not acoustic call boundaries."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .ebird_export import Detection

FIELDS = ["group_id", "recording", "species", "start_seconds", "end_seconds",
          "raw_detections", "estimated_count", "status", "reason", "detections",
          "reviewed_call_count"]


@dataclass
class CallGroup:
    detections: list[Detection]
    reason: str = ""
    reviewed_count: int | None = None

    @property
    def group_id(self) -> str:
        # Include source identities and confidence so changed model results cannot
        # silently inherit a review. Sorting makes row order immaterial.
        payload = sorted((d.recording, d.analyzer, d.source_label,
                          d.taxon.common_name, d.taxon.scientific_name,
                          d.start_seconds, d.end_seconds, str(d.confidence))
                         for d in self.detections)
        return hashlib.sha256(json.dumps([1, payload]).encode()).hexdigest()[:24]

    @property
    def count(self) -> int:
        if self.reviewed_count is not None:
            return self.reviewed_count
        return 1


def group_calls(detections: list[Detection]) -> list[CallGroup]:
    """Group one recording/taxon; never combine merely nearby non-overlapping calls.

    Each connected group of overlapping or touching windows estimates one event.
    Positive gaps keep groups separate. Diagnostic reasons flag weak overlaps,
    chains, or differing labels without requiring review. This can undercount
    repeated calls; it does not segment audio or count individual birds.
    """
    valid, groups = [], []
    invalid = {}
    for detection in detections:
        if not detection.contributes_nfc_count:
            continue
        if (not math.isfinite(detection.start_seconds)
                or not math.isfinite(detection.end_seconds)
                or detection.start_seconds < 0
                or detection.end_seconds <= detection.start_seconds):
            group = CallGroup([detection], "Invalid detection interval")
            invalid.setdefault(group.group_id, []).append(detection)
        else:
            valid.append(detection)
    groups.extend(CallGroup(values, "Invalid detection interval") for values in invalid.values())
    valid.sort(key=lambda d: (d.start_seconds, d.end_seconds, d.analyzer, d.source_label))
    cluster = []
    end = -1.0

    def finish():
        if not cluster:
            return
        reason = ""
        if len(cluster) > 1:
            common = min(d.end_seconds for d in cluster) - max(d.start_seconds for d in cluster)
            longest = max(d.end_seconds - d.start_seconds for d in cluster)
            labels = {d.source_label for d in cluster if d.analyzer == "Nighthawk"}
            if len(labels) > 1:
                reason = "Different Nighthawk labels mapped to the same taxon"
            elif common / longest < 0.8:
                reason = "Partial, touching, or chained windows; call count uncertain"
        groups.append(CallGroup(list(cluster), reason))

    for detection in valid:
        if cluster and detection.start_seconds > end:
            finish()
            cluster = []
        cluster.append(detection)
        end = max(end, detection.end_seconds)
    finish()
    return groups


def read_reviews(path: Path) -> dict[str, int]:
    """Reject malformed manual input before any export files are overwritten."""
    if not path.exists():
        return {}
    reviews = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not {"group_id", "reviewed_call_count"}.issubset(reader.fieldnames or []):
            raise ValueError(f"{path.name}: missing group_id or reviewed_call_count column")
        seen = set()
        for row in reader:
            key = row["group_id"]
            if not key or key in seen:
                raise ValueError(f"{path.name}: missing or duplicate group_id")
            seen.add(key)
            value = (row.get("reviewed_call_count") or "").strip()
            if value:
                if not value.isascii() or not value.isdigit():
                    raise ValueError(f"{path.name}: reviewed_call_count must be a nonnegative integer ({key})")
                reviews[key] = int(value)
    return reviews


def write_groups(path: Path, groups: list[CallGroup], reviews: dict[str, int]) -> None:
    rows = []
    current_ids = {group.group_id for group in groups}
    # Do not silently discard reviewed groups when source data changes.
    if path.exists() and set(reviews) - current_ids:
        backup = path.with_name(f"{path.stem}.previous-{time.time_ns()}.csv")
        backup.write_bytes(path.read_bytes())
    for group in groups:
        d = group.detections[0]
        rows.append(dict(
            group_id=group.group_id, recording=d.recording, species=d.taxon.common_name,
            start_seconds=min(x.start_seconds for x in group.detections),
            end_seconds=max(x.end_seconds for x in group.detections),
            raw_detections=len(group.detections),
            estimated_count=group.count,
            status="reviewed" if group.reviewed_count is not None else "automatic",
            reason=group.reason,
            detections=" | ".join(f"{x.analyzer}:{x.source_label} {x.start_seconds:g}-{x.end_seconds:g}s" for x in group.detections),
            reviewed_call_count="" if group.reviewed_count is None else group.reviewed_count))
    staged = path.with_suffix(".tmp")
    with staged.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    staged.replace(path)
