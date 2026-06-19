"""Automated night-readiness checks for the local web UI."""
from __future__ import annotations

import asyncio
import platform
import shutil
import struct
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from . import installer
from .devices import list_input_devices
from .paths import night_dir, recordings_root_path
from .power import current_power_snapshot
from .recorder import measure_levels, record_test_clip_variant
from .scheduler import next_relevant_window
from .sounddevice_diagnostics import record_sounddevice_test, stop_sounddevice_preview_meter
from .weather import environmental_snapshot

STATUS_READY = "ready"
STATUS_NOTE = "note"
STATUS_PROBLEM = "problem"
STATUS_NOT_CHECKED = "not_checked"


READINESS_GROUPS = [
    {
        "id": "recording_input",
        "title": "Recording Input",
        "checks": [
            {
                "id": "microphone_open",
                "label": "Configured microphone is available and can be opened.",
            },
            {
                "id": "input_signal",
                "label": "Input signal is present.",
            },
            {
                "id": "test_recording",
                "label": "Test recording produces usable audio.",
            },
        ],
    },
    {
        "id": "storage",
        "title": "Storage",
        "checks": [
            {
                "id": "save_location",
                "label": "Save location exists, is writable, and has enough free space for the expected recording.",
            },
            {
                "id": "output_folders",
                "label": "Output folders can be created and written.",
            },
        ],
    },
    {
        "id": "overnight_reliability",
        "title": "Overnight Reliability",
        "checks": [
            {
                "id": "power_source",
                "label": "Power source is suitable for the planned recording.",
            },
            {
                "id": "single_session",
                "label": "Only one NFC Tools session is active.",
            },
        ],
    },
    {
        "id": "supporting_services",
        "title": "Supporting Services",
        "checks": [
            {
                "id": "analyzers",
                "label": "Enabled analyzers are installed and runnable.",
            },
            {
                "id": "environment_logging",
                "label": "Environment logging is working.",
            },
        ],
    },
]


@dataclass
class ReadinessCheck:
    id: str
    status: str
    detail: str
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "detail": self.detail,
            **(self.extra or {}),
        }


def initial_readiness_groups() -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group in READINESS_GROUPS:
        groups.append({
            "id": group["id"],
            "title": group["title"],
            "checks": [
                {
                    "id": check["id"],
                    "label": check["label"],
                    "status": STATUS_NOT_CHECKED,
                    "detail": "",
                }
                for check in group["checks"]
            ],
        })
    return groups


def grouped_results(results: list[ReadinessCheck]) -> list[dict[str, Any]]:
    by_id = {result.id: result.to_dict() for result in results}
    groups = initial_readiness_groups()
    for group in groups:
        for check in group["checks"]:
            check.update(by_id.get(check["id"], {}))
    return groups


def _human_bytes(value: float | int) -> str:
    size = float(max(0, value))
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "bytes":
                return f"{int(size)} bytes"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _scheduled_window(cfg) -> tuple[datetime, datetime, str]:
    win = next_relevant_window(datetime.now(), cfg.schedule.start_time, cfg.schedule.end_time, cfg.site.timezone)
    return win.starts_at, win.ends_at, win.session_date.isoformat()


def _recording_window_hours(starts_at: datetime, ends_at: datetime) -> float:
    return max(0.0, (ends_at - starts_at).total_seconds()) / 3600


def _estimated_session_bytes(cfg, hours: float) -> int:
    bytes_per_sample = 4 if int(cfg.recording.bit_depth or 16) > 16 else 2
    sample_rate = max(1, int(cfg.recording.sample_rate or 48000))
    channels = max(1, int(cfg.recording.channels or 1))
    return int(hours * 3600 * sample_rate * channels * bytes_per_sample)


def _select_recording_backend(cfg) -> str:
    backend = str(getattr(cfg.recording, "backend", "auto") or "auto").lower()
    if backend in {"sounddevice", "coreaudio", "sounddevice_coreaudio"}:
        return "sounddevice"
    if backend in {"ffmpeg", "avfoundation"}:
        return "ffmpeg"
    if platform.system() == "Darwin":
        return "sounddevice"
    return "ffmpeg"


def _configured_device(cfg) -> dict[str, Any] | None:
    dev_id = cfg.recording.device
    if not dev_id:
        return None
    return next((device for device in list_input_devices() if device.get("id") == dev_id), None)


def _signal_present(levels: dict[str, Any] | None) -> bool:
    if not levels:
        return False
    for key in ("rms_db", "mean_db", "level_db", "peak_db"):
        value = levels.get(key)
        try:
            if value is not None and float(value) > -90.0:
                return True
        except (TypeError, ValueError):
            continue
    for key in ("rms", "peak"):
        value = levels.get(key)
        try:
            if value is not None and float(value) > 0.00003:
                return True
        except (TypeError, ValueError):
            continue
    return False


async def _measure_input(cfg, device: dict[str, Any]) -> dict[str, Any]:
    backend = _select_recording_backend(cfg)
    if backend == "sounddevice":
        levels = await measure_sounddevice_level_for_readiness(cfg, device)
        return {"backend": backend, "opened": True, "levels": levels}

    levels = await measure_levels(device.get("ffmpeg_input", []), seconds=1)
    return {
        "backend": backend,
        "opened": levels.get("returncode") == 0,
        "levels": levels,
    }


async def measure_sounddevice_level_for_readiness(cfg, device: dict[str, Any]) -> dict[str, Any]:
    from .sounddevice_diagnostics import measure_sounddevice_preview_level

    return await measure_sounddevice_preview_level(
        sample_rate=max(8000, int(getattr(cfg.recording, "sample_rate", 48000) or 48000)),
        channels=max(1, int(getattr(cfg.recording, "channels", 1) or 1)),
        selected_name=device.get("name", ""),
    )


def _wav_info(path: Path) -> dict[str, Any]:
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
                audio_format, channels, sample_rate, byte_rate, block_align, bits_per_sample = struct.unpack("<HHIIHH", raw)
                fmt = {
                    "audio_format": int(audio_format),
                    "channels": int(channels),
                    "sample_rate": int(sample_rate),
                    "byte_rate": int(byte_rate),
                    "block_align": int(block_align),
                    "bits_per_sample": int(bits_per_sample),
                }
            elif chunk_id == b"data":
                data_size += int(chunk_size)
            f.seek(chunk_data_start + chunk_size + (chunk_size % 2))

    if not fmt:
        raise ValueError("missing WAV format chunk")
    if data_size <= 0:
        raise ValueError("missing or empty WAV data chunk")
    if fmt["byte_rate"] <= 0:
        raise ValueError("invalid WAV byte rate")
    return {
        **fmt,
        "data_size": data_size,
        "duration_seconds": data_size / fmt["byte_rate"],
    }


def _test_variant_for_recording_settings(cfg) -> str:
    preset = str(getattr(cfg.recording, "format_preset", "auto_native") or "auto_native").lower()
    if preset in {"auto", "auto_native", "native", "native_float"}:
        return "native_float"
    if preset in {"float_48k", "s16_48k"}:
        return preset
    return "current"


async def _record_test_clip(cfg, device: dict[str, Any], session_date: str) -> dict[str, Any]:
    await stop_sounddevice_preview_meter()
    diag_dir = night_dir(session_date, cfg.recording.save_location) / "diagnostics"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backend = _select_recording_backend(cfg)
    seconds = 3

    if backend == "sounddevice":
        wav_path = diag_dir / f"readiness_test_{stamp}_sounddevice.wav"
        result = await record_sounddevice_test(
            wav_path,
            seconds=seconds,
            sample_rate=max(8000, int(getattr(cfg.recording, "sample_rate", 48000) or 48000)),
            channels=max(1, int(getattr(cfg.recording, "channels", 1) or 1)),
            selected_name=device.get("name", ""),
        )
    else:
        variant = _test_variant_for_recording_settings(cfg)
        wav_path = diag_dir / f"readiness_test_{stamp}_{variant}.wav"
        result = await record_test_clip_variant(
            device.get("ffmpeg_input", []),
            wav_path,
            variant=variant,
            seconds=seconds,
            sample_rate=int(getattr(cfg.recording, "sample_rate", 48000) or 48000),
            channels=int(getattr(cfg.recording, "channels", 1) or 1),
            bit_depth=int(getattr(cfg.recording, "bit_depth", 32) or 32),
            diagnostics_metadata={
                "readiness_check": True,
                "configured_device_id": cfg.recording.device,
                "selected_device_name": device.get("name", ""),
                "site_name": cfg.site.name,
            },
        )

    if not result.get("ok"):
        raise RuntimeError(result.get("error") or result.get("stderr_tail") or "test recording did not complete")

    info = _wav_info(Path(result["wav_path"]))
    result["wav_info"] = info
    result["session_date"] = session_date
    result["download_url"] = f"/diagnostics/raw-recording-test/{session_date}/{result['wav_name']}"
    result["log_download_url"] = f"/diagnostics/raw-recording-test/{session_date}/{result['log_name']}"
    return result


def _check_storage(cfg, starts_at: datetime, ends_at: datetime) -> list[ReadinessCheck]:
    root = recordings_root_path(cfg.recording.save_location)
    hours = _recording_window_hours(starts_at, ends_at)
    expected = _estimated_session_bytes(cfg, hours)
    margin = int(expected * 1.2)

    if not root.exists():
        return [
            ReadinessCheck(
                "save_location",
                STATUS_PROBLEM,
                f"Save location was not found: {root}",
            ),
            ReadinessCheck(
                "output_folders",
                STATUS_PROBLEM,
                "Output folders cannot be checked until the save location is available.",
            ),
        ]

    if not root.is_dir():
        return [
            ReadinessCheck("save_location", STATUS_PROBLEM, f"Save location is not a folder: {root}"),
            ReadinessCheck("output_folders", STATUS_PROBLEM, "Output folders require a folder save location."),
        ]

    try:
        usage = shutil.disk_usage(root)
    except OSError as exc:
        return [
            ReadinessCheck("save_location", STATUS_NOTE, f"Free space could not be checked: {exc}"),
            _probe_output_folders(root),
        ]

    try:
        with tempfile.NamedTemporaryFile(prefix=".nfc_tools_write_", dir=root, delete=True) as f:
            f.write(b"readiness")
            f.flush()
    except OSError as exc:
        return [
            ReadinessCheck("save_location", STATUS_PROBLEM, f"Save location is not writable: {exc}"),
            ReadinessCheck("output_folders", STATUS_PROBLEM, "Output folders cannot be created without write access."),
        ]

    if usage.free < expected:
        storage_status = STATUS_PROBLEM
        detail = f"{_human_bytes(usage.free)} free; expected recording needs about {_human_bytes(expected)}."
    elif usage.free < margin:
        storage_status = STATUS_NOTE
        detail = f"{_human_bytes(usage.free)} free; expected recording needs about {_human_bytes(expected)}."
    else:
        storage_status = STATUS_READY
        detail = f"{_human_bytes(usage.free)} free; expected recording needs about {_human_bytes(expected)}."

    return [
        ReadinessCheck("save_location", storage_status, detail),
        _probe_output_folders(root),
    ]


def _probe_output_folders(root: Path) -> ReadinessCheck:
    try:
        with tempfile.TemporaryDirectory(prefix=".nfc_tools_readiness_", dir=root) as tmp:
            probe = Path(tmp)
            for name in ("audio", "results", "logs"):
                folder = probe / name
                folder.mkdir()
                test_file = folder / ".write-test"
                test_file.write_text("ok", encoding="utf-8")
        return ReadinessCheck("output_folders", STATUS_READY, "Audio, results, and logs folders can be created.")
    except OSError as exc:
        return ReadinessCheck("output_folders", STATUS_PROBLEM, f"Output folder probe failed: {exc}")


def _check_power() -> ReadinessCheck:
    snapshot = current_power_snapshot()
    percent = f" ({snapshot.battery_percent}% battery)" if snapshot.battery_percent is not None else ""
    if not snapshot.available:
        return ReadinessCheck("power_source", STATUS_NOTE, "Power source could not be checked on this system.")
    if snapshot.on_battery is True:
        return ReadinessCheck("power_source", STATUS_NOTE, f"Computer is running on battery{percent}.")
    if snapshot.on_battery is False:
        return ReadinessCheck("power_source", STATUS_READY, f"Computer is connected to power{percent}.")
    return ReadinessCheck("power_source", STATUS_NOTE, "Power source is unknown.")


def _check_single_session(active_session_status: dict | None, cfg, session_date: str) -> ReadinessCheck:
    lock_dir = recordings_root_path(cfg.recording.save_location) / session_date / ".analysis_lock"
    if lock_dir.exists():
        return ReadinessCheck("single_session", STATUS_PROBLEM, f"An analysis lock already exists for {session_date}.")
    if active_session_status and active_session_status.get("state") in {"recording", "awaiting_start", "stopping"}:
        return ReadinessCheck("single_session", STATUS_READY, "This app is managing the active session.")
    return ReadinessCheck("single_session", STATUS_READY, "This app has no active recording session.")


def _check_analyzers(cfg) -> ReadinessCheck:
    enabled = list(cfg.analyzers.enabled or [])
    if not enabled:
        return ReadinessCheck("analyzers", STATUS_NOTE, "No analyzers are enabled.")
    status = installer.status()
    missing = [name for name in enabled if not status.get(name, {}).get("installed")]
    if missing:
        labels = ", ".join(_analyzer_label(name) for name in missing)
        return ReadinessCheck("analyzers", STATUS_NOTE, f"{labels} will need install/repair before analysis can run.")
    labels = ", ".join(_analyzer_label(name) for name in enabled)
    return ReadinessCheck("analyzers", STATUS_READY, f"Enabled analyzers are ready: {labels}.")


def _analyzer_label(name: str) -> str:
    labels = {"birdnet": "BirdNET", "nighthawk": "Nighthawk"}
    return labels.get(name.lower(), name)


async def _check_environment(cfg) -> ReadinessCheck:
    row = await asyncio.to_thread(
        environmental_snapshot,
        cfg.site.latitude,
        cfg.site.longitude,
        cfg.site.timezone,
        datetime.now(),
    )
    if row.get("available"):
        return ReadinessCheck("environment_logging", STATUS_READY, "Weather data was retrieved for the current hour.")
    note = row.get("notes") or "Weather data could not be retrieved."
    return ReadinessCheck("environment_logging", STATUS_NOTE, note)


async def run_readiness_checks(cfg, active_session_status: dict | None = None) -> list[dict[str, Any]]:
    starts_at, ends_at, session_date = _scheduled_window(cfg)
    results: list[ReadinessCheck] = []

    device = _configured_device(cfg)
    measure_result: dict[str, Any] | None = None
    if not cfg.recording.device:
        results.extend([
            ReadinessCheck("microphone_open", STATUS_PROBLEM, "No microphone is configured."),
            ReadinessCheck("input_signal", STATUS_PROBLEM, "Input signal cannot be checked without a configured microphone."),
            ReadinessCheck("test_recording", STATUS_PROBLEM, "Test recording cannot run without a configured microphone."),
        ])
    elif not device:
        results.extend([
            ReadinessCheck("microphone_open", STATUS_PROBLEM, "Configured microphone was not found."),
            ReadinessCheck("input_signal", STATUS_PROBLEM, "Input signal cannot be checked until the microphone is available."),
            ReadinessCheck("test_recording", STATUS_PROBLEM, "Test recording cannot run until the microphone is available."),
        ])
    else:
        try:
            measure_result = await _measure_input(cfg, device)
            if measure_result.get("opened"):
                results.append(ReadinessCheck("microphone_open", STATUS_READY, f"Opened {device.get('name', 'configured microphone')}."))
            else:
                detail = measure_result.get("levels", {}).get("stderr_tail") or "The recording backend could not open the microphone."
                results.append(ReadinessCheck("microphone_open", STATUS_PROBLEM, detail))
        except Exception as exc:  # noqa: BLE001
            results.append(ReadinessCheck("microphone_open", STATUS_PROBLEM, f"Microphone could not be opened: {exc}"))

        if measure_result and measure_result.get("opened") and _signal_present(measure_result.get("levels")):
            results.append(ReadinessCheck("input_signal", STATUS_READY, "Input signal was detected."))
        else:
            results.append(ReadinessCheck("input_signal", STATUS_PROBLEM, "No usable input signal was detected."))

        if any(result.id == "microphone_open" and result.status == STATUS_READY for result in results):
            try:
                test = await _record_test_clip(cfg, device, session_date)
                info = test["wav_info"]
                if info["duration_seconds"] < 1.0:
                    results.append(ReadinessCheck("test_recording", STATUS_PROBLEM, "Test recording was shorter than expected."))
                else:
                    detail = (
                        f"Created {test['wav_name']} "
                        f"({info['duration_seconds']:.1f}s, {info['sample_rate']} Hz, {info['channels']} channel(s))."
                    )
                    results.append(ReadinessCheck(
                        "test_recording",
                        STATUS_READY,
                        detail,
                        {
                            "audio_url": test.get("download_url", ""),
                            "log_url": test.get("log_download_url", ""),
                            "file_name": test.get("wav_name", ""),
                        },
                    ))
            except Exception as exc:  # noqa: BLE001
                results.append(ReadinessCheck("test_recording", STATUS_PROBLEM, f"Test recording failed: {exc}"))

    results.extend(_check_storage(cfg, starts_at, ends_at))
    results.append(_check_power())
    results.append(_check_single_session(active_session_status, cfg, session_date))
    results.append(_check_analyzers(cfg))
    results.append(await _check_environment(cfg))

    return grouped_results(results)
