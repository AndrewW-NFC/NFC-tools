"""Imported-recording planning routes."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import wave
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from .. import config as config_mod
from ..ffmpeg_locator import find_ffmpeg
from ..folder_picker import FolderPickerUnavailable, choose_directory
from .geocode import timezone_for_coordinates
from .state import state

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()

SOURCE_AUDIO_FORMATS = {
    "AIFF": {".aif", ".aiff"},
    "FLAC": {".flac"},
    "M4A": {".m4a"},
    "MP3": {".mp3"},
    "OGG": {".ogg"},
    "WAV": {".wav", ".wave"},
}
AUDIO_EXTENSIONS = {ext for extensions in SOURCE_AUDIO_FORMATS.values() for ext in extensions}
REVIEW_FILE_LIMIT = 200
FILENAME_TIME_RE = re.compile(
    r"(?P<year>20\d{2})[-_]?(?P<month>\d{2})[-_]?(?P<day>\d{2})"
    r"(?:[^\d]+|T)"
    r"(?P<hour>\d{2})[-_:]?(?P<minute>\d{2})"
    r"(?:[-_:]?(?P<second>\d{2}))?"
)
FFMPEG_DURATION_RE = re.compile(r"Duration:\s*(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+(?:\.\d+)?)")


def _format_label_for_suffix(suffix: str) -> str:
    normalized = suffix.lower()
    for label, extensions in SOURCE_AUDIO_FORMATS.items():
        if normalized in extensions:
            return label
    return normalized.lstrip(".").upper()


def _display_path(path: Path) -> str:
    try:
        return "~/" + str(path.expanduser().relative_to(Path.home()))
    except ValueError:
        return str(path)


def _human_bytes(value: int | float) -> str:
    amount = float(max(0, value))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"


def _wav_duration_seconds(path: Path) -> float | None:
    if path.suffix.lower() not in {".wav", ".wave"}:
        return None
    try:
        with wave.open(str(path), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            if frame_rate <= 0:
                return None
            return round(wav_file.getnframes() / frame_rate, 3)
    except (wave.Error, OSError, EOFError):
        return None


def _ffmpeg_duration_seconds(path: Path, ffmpeg_path: str | None) -> float | None:
    if not ffmpeg_path:
        return None
    try:
        result = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-i", str(path)],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    output = f"{result.stderr}\n{result.stdout}"
    match = FFMPEG_DURATION_RE.search(output)
    if not match:
        return None

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = float(match.group("seconds"))
    return round(hours * 3600 + minutes * 60 + seconds, 3)


def _duration_seconds(path: Path, ffmpeg_path: str | None = None) -> float | None:
    return _wav_duration_seconds(path) or _ffmpeg_duration_seconds(path, ffmpeg_path)


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown"
    whole = int(round(seconds))
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _detected_start_from_name(name: str) -> str | None:
    match = FILENAME_TIME_RE.search(name)
    if not match:
        return None
    second = match.group("second") or "00"
    return (
        f"{match.group('year')}-{match.group('month')}-{match.group('day')} "
        f"{match.group('hour')}:{match.group('minute')}:{second}"
    )


def _scan_audio_folder(root: Path) -> dict:
    samples = []
    review_files = []
    errors = []
    audio_count = 0
    source_bytes = 0
    extension_counts: dict[str, int] = {}
    ffmpeg_path = find_ffmpeg()

    def on_error(error: OSError) -> None:
        errors.append(str(error))

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=on_error, followlinks=False):
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            path = Path(dirpath) / filename
            suffix = path.suffix.lower()
            if suffix not in AUDIO_EXTENSIONS:
                continue

            try:
                stat = path.stat()
            except OSError as exc:
                errors.append(f"{filename}: {exc}")
                continue

            audio_count += 1
            source_bytes += stat.st_size
            format_label = _format_label_for_suffix(suffix)
            extension_counts[format_label] = extension_counts.get(format_label, 0) + 1

            should_include_review_file = len(review_files) < REVIEW_FILE_LIMIT
            should_include_sample = len(samples) < 12
            if should_include_review_file or should_include_sample:
                duration = _duration_seconds(path, ffmpeg_path)
                file_record = {
                    "name": filename,
                    "relative_path": str(path.relative_to(root)),
                    "size_bytes": stat.st_size,
                    "size_display": _human_bytes(stat.st_size),
                    "duration_seconds": duration,
                    "duration_display": _format_duration(duration),
                    "detected_start": _detected_start_from_name(filename),
                }
                if should_include_review_file:
                    review_files.append(file_record)
                if should_include_sample:
                    samples.append(file_record)

    return {
        "audio_count": audio_count,
        "source_bytes": source_bytes,
        "source_display": _human_bytes(source_bytes),
        "extension_counts": extension_counts,
        "samples": samples,
        "review_files": review_files,
        "review_file_count": len(review_files),
        "review_file_limit": REVIEW_FILE_LIMIT,
        "review_hidden_count": max(0, audio_count - len(review_files)),
        "errors": errors[:20],
    }


def _storage_estimate(source_bytes: int, audio_count: int, available_bytes: int) -> dict:
    if audio_count <= 0:
        processed_low = processed_high = 0
        analyzer_low = analyzer_high = 0
        clip_low = clip_high = 0
    else:
        processed_low = processed_high = source_bytes
        analyzer_low = max(audio_count * 64 * 1024, int(source_bytes * 0.001))
        analyzer_high = max(audio_count * 2 * 1024 * 1024, int(source_bytes * 0.01))
        clip_low = int(source_bytes * 0.02)
        clip_high = int(source_bytes * 0.30)

    total_low = processed_low + analyzer_low + clip_low
    total_high = processed_high + analyzer_high + clip_high
    if total_high <= available_bytes:
        status = "enough"
        message = "The output location appears to have enough free space for this early estimate."
    elif total_low <= available_bytes:
        status = "tight"
        message = "This may fit, but clip storage is uncertain. Use a larger output drive if possible."
    else:
        status = "over"
        message = "This is likely to exceed the free space in the selected output location."

    return {
        "processed_audio": {
            "low_bytes": processed_low,
            "high_bytes": processed_high,
            "display": _human_bytes(processed_high),
        },
        "analyzer_results": {
            "low_bytes": analyzer_low,
            "high_bytes": analyzer_high,
            "display": f"{_human_bytes(analyzer_low)} to {_human_bytes(analyzer_high)}",
        },
        "clips": {
            "low_bytes": clip_low,
            "high_bytes": clip_high,
            "display": f"{_human_bytes(clip_low)} to {_human_bytes(clip_high)}",
        },
        "total": {
            "low_bytes": total_low,
            "high_bytes": total_high,
            "display": f"{_human_bytes(total_low)} to {_human_bytes(total_high)}",
        },
        "status": status,
        "message": message,
    }


def _folder_choice_response(current_path: str, *, title: str) -> JSONResponse:
    try:
        selected = choose_directory(current_path, title=title)
    except FolderPickerUnavailable as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)

    if selected is None:
        return JSONResponse({"ok": False, "cancelled": True})

    return JSONResponse({"ok": True, "path": selected, "display": _display_path(Path(selected))})


def _timezone_for_import_site(latitude: float, longitude: float, fallback: str) -> str:
    return config_mod.normalize_timezone(timezone_for_coordinates(latitude, longitude), fallback)


@router.get("/import-recordings", response_class=HTMLResponse)
def import_recordings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "import_recordings.html",
        {
            "cfg": state.cfg.model_dump(),
            "audio_formats": ", ".join(SOURCE_AUDIO_FORMATS.keys()),
        },
    )


@router.post("/import-recordings/choose-source-folder")
async def choose_source_folder(request: Request):
    form = await request.form()
    current_path = str(form.get("current_source_folder", "") or "")
    return _folder_choice_response(current_path, title="Choose folder with recordings to process")


@router.post("/import-recordings/choose-output-folder")
async def choose_output_folder(request: Request):
    form = await request.form()
    current_path = str(form.get("current_output_folder", "") or "")
    return _folder_choice_response(current_path, title="Choose where NFC Tools writes processed recordings")


@router.post("/import-recordings/scan")
def scan_import_recordings(
    source_folder: str = Form(...),
    output_folder: str = Form(...),
):
    source_path = Path(source_folder).expanduser()
    output_path = Path(output_folder).expanduser()
    if not source_path.is_dir():
        return JSONResponse({"ok": False, "error": "Choose an existing source folder."}, status_code=400)
    if not output_path.is_dir():
        return JSONResponse({"ok": False, "error": "Choose an existing output folder."}, status_code=400)

    scan = _scan_audio_folder(source_path)
    disk = shutil.disk_usage(output_path)
    estimate = _storage_estimate(scan["source_bytes"], scan["audio_count"], disk.free)

    warnings = []
    try:
        source_resolved = source_path.resolve()
        output_resolved = output_path.resolve()
        if source_resolved == output_resolved:
            warnings.append(
                "The source and output folders are the same. Choose a separate output folder before processing."
            )
        elif output_resolved in source_resolved.parents:
            warnings.append("The output folder contains the source folder. A separate output drive or folder is safer.")
        elif source_resolved in output_resolved.parents:
            warnings.append("The output folder is inside the source folder. Future scans may include processed files.")
    except OSError:
        pass

    return JSONResponse(
        {
            "ok": True,
            "source": {
                "path": str(source_path),
                "display": _display_path(source_path),
                **scan,
            },
            "output": {
                "path": str(output_path),
                "display": _display_path(output_path),
                "total_bytes": disk.total,
                "used_bytes": disk.used,
                "free_bytes": disk.free,
                "total_display": _human_bytes(disk.total),
                "free_display": _human_bytes(disk.free),
            },
            "estimate": estimate,
            "warnings": warnings,
        }
    )


@router.post("/import-recordings/site-timezone")
async def import_site_timezone(
    latitude: float = Form(...),
    longitude: float = Form(...),
    fallback: str = Form(""),
):
    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return JSONResponse({"error": "invalid coordinates"}, status_code=400)

    timezone = _timezone_for_import_site(
        latitude,
        longitude,
        fallback or state.cfg.site.timezone,
    )
    return JSONResponse(
        {
            "ok": True,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
        }
    )
