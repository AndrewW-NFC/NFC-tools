"""Export short review clips from analyzer result labels."""

from __future__ import annotations

import csv
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg_locator import ensure_ffmpeg
from .filenames import parse as parse_recording_name
from .logging_setup import get

log = get("clip_exporter")


@dataclass(frozen=True)
class ClipSpec:
    start_seconds: float
    end_seconds: float
    label: str
    analyzer_label: str


def export_analyzer_clips(
    wav_path: Path,
    analyzer: str,
    output_dir: Path,
    clips_root: Path,
    cfg,
) -> int:
    """Export review clips for one analyzer's output from one recording."""
    specs = list(_clip_specs(analyzer, output_dir, cfg))
    if not specs:
        return 0

    destination = clips_root / _segment_folder_name(wav_path)
    destination.mkdir(parents=True, exist_ok=True)
    ffmpeg = ensure_ffmpeg()

    exported = 0
    for spec in specs:
        if spec.end_seconds <= spec.start_seconds:
            continue
        out_path = _unique_clip_path(destination, spec.label, spec.analyzer_label)
        _export_clip(ffmpeg, wav_path, out_path, spec.start_seconds, spec.end_seconds)
        exported += 1

    return exported


def _clip_specs(analyzer: str, output_dir: Path, cfg) -> list[ClipSpec]:
    name = analyzer.lower()
    if name == "nighthawk":
        return _nighthawk_clip_specs(output_dir)
    if name == "birdnet":
        threshold = float(getattr(getattr(cfg, "analyzers", None), "birdnet_min_conf", 0.25))
        return _birdnet_clip_specs(output_dir, threshold)
    return []


def _nighthawk_clip_specs(output_dir: Path) -> list[ClipSpec]:
    specs: list[ClipSpec] = []
    for path in sorted(output_dir.rglob("*audacity*.txt")):
        try:
            with path.open(newline="") as f:
                for row in csv.reader(f, delimiter="\t"):
                    if len(row) < 3:
                        continue
                    start = _float(row[0])
                    end = _float(row[1])
                    label = row[2].strip()
                    if start is None or end is None or not label:
                        continue
                    specs.append(ClipSpec(start, end, label, "Nighthawk"))
        except Exception as e:  # noqa: BLE001
            log.warning("could not parse Nighthawk labels: path=%s error=%s", path, e)
    return specs


def _birdnet_clip_specs(output_dir: Path, threshold: float) -> list[ClipSpec]:
    # NFC Tools asks BirdNET for both table and CSV results. The table output
    # includes BirdNET's Species Code, so use it first and avoid duplicate clips.
    table_paths = sorted(output_dir.rglob("*.selection.table.txt"))
    table_specs = _birdnet_clip_specs_from_paths(table_paths, threshold)
    if table_specs:
        return table_specs

    fallback_paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".csv"}
    )
    return _birdnet_clip_specs_from_paths(fallback_paths, threshold)


def _birdnet_clip_specs_from_paths(paths: list[Path], threshold: float) -> list[ClipSpec]:
    specs: list[ClipSpec] = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in {".txt", ".csv"}:
            continue
        try:
            parsed = _birdnet_specs_from_file(path, threshold)
        except Exception as e:  # noqa: BLE001
            log.warning("could not parse BirdNET results: path=%s error=%s", path, e)
            continue
        specs.extend(parsed)
    return specs


def _birdnet_specs_from_file(path: Path, threshold: float) -> list[ClipSpec]:
    with path.open(newline="") as f:
        sample = f.readline()
        if not sample:
            return []
        delimiter = "\t" if "\t" in sample else ","
        f.seek(0)
        reader = csv.DictReader(f, delimiter=delimiter)
        if not reader.fieldnames:
            return []

        fields = {field.strip(): field for field in reader.fieldnames}
        start_field = fields.get("Begin Time (s)") or fields.get("Start (s)")
        end_field = fields.get("End Time (s)") or fields.get("End (s)")
        confidence_field = fields.get("Confidence")
        code_field = fields.get("Species Code")
        common_field = fields.get("Common Name") or fields.get("Common name")
        if not start_field or not end_field or not confidence_field:
            return []

        specs: list[ClipSpec] = []
        for row in reader:
            confidence = _float(row.get(confidence_field))
            if confidence is None or confidence < threshold:
                continue

            code = (row.get(code_field) or "").strip() if code_field else ""
            common = (row.get(common_field) or "").strip() if common_field else ""
            category = code or common
            if not category or category.lower() == "nocall":
                continue

            start = _float(row.get(start_field))
            end = _float(row.get(end_field))
            if start is None or end is None:
                continue
            label = f"{category} ({_format_probability(confidence)})"
            specs.append(ClipSpec(start, end, label, "BirdNET"))
        return specs


def _export_clip(
    ffmpeg: str,
    wav_path: Path,
    out_path: Path,
    start_seconds: float,
    end_seconds: float,
) -> None:
    duration = max(0, end_seconds - start_seconds)
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-y",
        "-ss",
        f"{max(0, start_seconds):.6f}",
        "-t",
        f"{duration:.6f}",
        "-i",
        str(wav_path),
        "-map",
        "0:a:0",
        "-c:a",
        "copy",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def _segment_folder_name(wav_path: Path) -> str:
    parsed = parse_recording_name(wav_path.name)
    if parsed:
        return parsed.recorded_at.strftime("%H-%M-%S")
    return wav_path.stem


def _unique_clip_path(directory: Path, label: str, analyzer_label: str) -> Path:
    stem = f"{_safe_filename(label)}-{analyzer_label}"
    path = directory / f"{stem}.wav"
    if not path.exists():
        return path

    index = 2
    while True:
        path = directory / f"{stem} {index}.wav"
        if not path.exists():
            return path
        index += 1


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|]+", "-", value.strip())
    safe = re.sub(r"\s+", " ", safe).strip(" .")
    return safe or "clip"


def _format_probability(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _float(value) -> float | None:
    try:
        return float(str(value).strip())
    except Exception:  # noqa: BLE001
        return None
