"""Export short review clips from analyzer result labels."""

from __future__ import annotations

import csv
import math
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

from .birdnet_policy import keep_detection
from .clip_metadata import build_metadata, embed_metadata
from .ffmpeg_locator import ensure_ffmpeg
from .filenames import parse as parse_recording_name
from .logging_setup import get

log = get("clip_exporter")
REVIEW_CONTEXT_SECONDS = 4.0
# BirdNET 2.4 non-avian sound classes without numeric taxon IDs.
BIRDNET_NON_AVIAN_CODES = frozenset({
    "dogdog", "engine", "envrnm", "frwrks", "gungun", "humnov",
    "humvoc", "humwhi", "powtoo", "siren1",
})


@dataclass(frozen=True)
class ClipSpec:
    start_seconds: float
    end_seconds: float
    label: str
    analyzer_label: str
    identification: str | None = None
    score: float | None = None


def export_analyzer_clips(
    wav_path: Path,
    analyzer: str,
    output_dir: Path,
    clips_root: Path,
    cfg,
) -> int:
    """Export review clips for one analyzer's output from one recording."""
    specs = list(_clip_specs(analyzer, output_dir, cfg))
    destination = clips_root / _segment_folder_name(wav_path)
    destination.mkdir(parents=True, exist_ok=True)
    if not specs:
        return 0
    ffmpeg = ensure_ffmpeg()
    wav_duration = _wav_duration_seconds(wav_path)

    exported = 0
    occurrences: dict[str, int] = {}
    for spec in specs:
        if spec.end_seconds <= spec.start_seconds:
            continue
        start_seconds, end_seconds = _review_interval(
            spec.start_seconds,
            spec.end_seconds,
            wav_duration,
        )
        if end_seconds <= start_seconds:
            continue
        stem = f"{_safe_filename(spec.label)}-{spec.analyzer_label}"
        occurrences[stem] = occurrences.get(stem, 0) + 1
        index = occurrences[stem]
        out_path = destination / f"{stem}{' ' + str(index) if index > 1 else ''}.wav"
        # Stable names prevent duplicate clips on retry. Publish each complete clip
        # atomically so an interrupted export cannot replace it with partial audio.
        with tempfile.TemporaryDirectory(prefix=".clip-", dir=destination) as temporary:
            staged = Path(temporary) / out_path.name
            _export_clip(ffmpeg, wav_path, staged, start_seconds, end_seconds)
            embed_metadata(staged, build_metadata(wav_path, spec, start_seconds, end_seconds, cfg))
            staged.replace(out_path)
        exported += 1

    return exported


def _clip_specs(analyzer: str, output_dir: Path, cfg) -> list[ClipSpec]:
    name = analyzer.lower()
    if name in {"nighthawk", "wingbeats"}:
        return _nighthawk_clip_specs(output_dir, "Wingbeats" if name == "wingbeats" else "Nighthawk")
    if name == "birdnet":
        threshold = float(getattr(getattr(cfg, "analyzers", None), "birdnet_min_conf", 0.500))
        return _birdnet_clip_specs(output_dir, threshold, getattr(cfg, "analyzers", None))
    return []


def _nighthawk_clip_specs(output_dir: Path, analyzer_label: str = "Nighthawk") -> list[ClipSpec]:
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
                    match = re.fullmatch(r"(.+) \(([0-9.]+)\)", label)
                    identification = match[1] if match else label
                    score = _float(match[2]) if match else None
                    specs.append(ClipSpec(start, end, label, analyzer_label, identification, score))
        except Exception as e:  # noqa: BLE001
            log.warning("could not parse Nighthawk labels: path=%s error=%s", path, e)
    return specs


def _birdnet_clip_specs(output_dir: Path, threshold: float, analyzers=None) -> list[ClipSpec]:
    # NFC Tools asks BirdNET for both table and CSV results. The table output
    # includes BirdNET's Species Code, so use it first and avoid duplicate clips.
    table_paths = sorted(output_dir.rglob("*.selection.table.txt"))
    table_specs = _birdnet_clip_specs_from_paths(table_paths, threshold, analyzers)
    if table_specs:
        return table_specs

    fallback_paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".csv"}
    )
    return _birdnet_clip_specs_from_paths(fallback_paths, threshold, analyzers)


def _birdnet_clip_specs_from_paths(paths: list[Path], threshold: float, analyzers=None) -> list[ClipSpec]:
    specs: list[ClipSpec] = []
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in {".txt", ".csv"}:
            continue
        try:
            parsed = _birdnet_specs_from_file(path, threshold, analyzers)
        except Exception as e:  # noqa: BLE001
            log.warning("could not parse BirdNET results: path=%s error=%s", path, e)
            continue
        specs.extend(parsed)
    return specs


def _birdnet_specs_from_file(path: Path, threshold: float, analyzers=None) -> list[ClipSpec]:
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
            if confidence is None:
                continue
            if analyzers is not None:
                if not keep_detection(row, analyzers):
                    continue
            elif confidence < threshold:
                continue

            code = (row.get(code_field) or "").strip() if code_field else ""
            common = (row.get(common_field) or "").strip() if common_field else ""
            # New Analyzer falls back to a full scientific_common label when its
            # eBird mapping lacks a code. Use the readable name in that case.
            category = (common if "_" in code else code) or common
            if not category or category.lower() == "nocall":
                continue

            start = _float(row.get(start_field))
            end = _float(row.get(end_field))
            if start is None or end is None:
                continue
            display_name = category
            if common and (code.lower().startswith("t-") or code.lower() in BIRDNET_NON_AVIAN_CODES):
                display_name = common
            label = f"{display_name} ({_format_probability(confidence)})"
            specs.append(ClipSpec(start, end, label, "BirdNET", category, confidence))
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
        "-map_metadata",
        "-1",
        "-fflags",
        "+bitexact",
        "-c:a",
        "copy",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)


def _review_interval(start_seconds: float, end_seconds: float, wav_duration: float) -> tuple[float, float]:
    start = max(0.0, start_seconds - REVIEW_CONTEXT_SECONDS)
    end = end_seconds + REVIEW_CONTEXT_SECONDS
    if wav_duration > 0:
        end = min(wav_duration, end)
    return start, end


def _wav_duration_seconds(path: Path) -> float:
    with path.open("rb") as f:
        header = f.read(12)
        if len(header) < 12:
            raise ValueError("file is too small to contain a WAV header")
        riff, _riff_size, wave_id = struct.unpack("<4sI4s", header)
        if riff != b"RIFF" or wave_id != b"WAVE":
            raise ValueError("file is not a RIFF/WAVE recording")

        fmt: dict[str, int] | None = None
        data_size = 0
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) == 0:
                break
            if len(chunk_header) < 8:
                raise ValueError("truncated WAV chunk header")

            chunk_id, chunk_size = struct.unpack("<4sI", chunk_header)
            chunk_data_start = f.tell()
            if chunk_id == b"fmt ":
                raw = f.read(min(chunk_size, 16))
                if len(raw) < 16:
                    raise ValueError("truncated WAV format chunk")
                (
                    _audio_format,
                    _channels,
                    _sample_rate,
                    byte_rate,
                    _block_align,
                    _bits_per_sample,
                ) = struct.unpack("<HHIIHH", raw)
                fmt = {"byte_rate": int(byte_rate)}
            elif chunk_id == b"data":
                data_size += int(chunk_size)

            f.seek(chunk_data_start + chunk_size + (chunk_size % 2))

    if not fmt:
        raise ValueError("missing WAV format chunk")
    if data_size <= 0:
        raise ValueError("missing or empty WAV data chunk")
    if fmt["byte_rate"] <= 0:
        raise ValueError("invalid WAV byte rate")
    return data_size / fmt["byte_rate"]


def _segment_folder_name(wav_path: Path) -> str:
    parsed = parse_recording_name(wav_path.name)
    if parsed:
        local = parsed.recorded_at
        name = local.strftime("%H-%M-%S")
        if local.utcoffset() is not None:
            name += local.astimezone(timezone.utc).strftime("_UTC-%H-%M-%S")
        return name
    return wav_path.stem


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|]+", "-", value.strip())
    safe = re.sub(r"\s+", " ", safe).strip(" .")
    return safe or "clip"


def _format_probability(value: float) -> str:
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def _float(value) -> float | None:
    try:
        number = float(str(value).strip())
        return number if math.isfinite(number) else None
    except Exception:  # noqa: BLE001
        return None
