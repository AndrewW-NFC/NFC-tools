"""Main HTTP routes: dashboard, settings, session control, and diagnostics."""

from __future__ import annotations

import asyncio
import platform
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, BackgroundTasks, Form, Query, Request, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import config as config_mod
from .. import doctor, installer
from ..devices import list_input_devices
from ..ephemeris import PRESETS, astronomical_nfc_window, civil_recording_window, preset_times
from ..folder_picker import FolderPickerUnavailable, choose_directory
from ..paths import recordings_root_path
from ..recorder import measure_levels
from ..schedule_resolver import (
    DEFAULT_TWILIGHT_PRESET,
    current_schedule_preview,
    next_window_for_config,
    schedule_uses_twilight,
)
from ..sounddevice_diagnostics import measure_sounddevice_preview_level, stop_sounddevice_preview_meter
from ..session import Session
from ..session_logging import latest_log_path, log_path_for_session_date, read_log_rows
from .geocode import timezone_for_coordinates
from .state import state

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()

def _scheduled_window_status() -> dict:
    try:
        zone = ZoneInfo(state.cfg.site.timezone)
    except ZoneInfoNotFoundError:
        zone = None
    now = datetime.now(zone) if zone else datetime.now()
    win = next_window_for_config(state.cfg, now)
    nfc_starts_at, nfc_ends_at = astronomical_nfc_window(
        win.session_date,
        state.cfg.site.latitude,
        state.cfg.site.longitude,
        state.cfg.site.timezone,
    )
    civil_starts_at, civil_ends_at = civil_recording_window(
        win.session_date,
        state.cfg.site.latitude,
        state.cfg.site.longitude,
        state.cfg.site.timezone,
    )

    return {
        "state": "idle",
        "session_date": win.session_date.isoformat(),
        "scheduled_starts_at": win.starts_at.isoformat(timespec="seconds"),
        "scheduled_ends_at": win.ends_at.isoformat(timespec="seconds"),
        "ends_at": win.ends_at.isoformat(timespec="seconds"),
        "civil_starts_at": civil_starts_at.isoformat(timespec="seconds"),
        "civil_ends_at": civil_ends_at.isoformat(timespec="seconds"),
        "nfc_starts_at": nfc_starts_at.isoformat(timespec="seconds"),
        "nfc_ends_at": nfc_ends_at.isoformat(timespec="seconds"),
        "recordings": [],
        "level_db": None,
    }


def _nfc_window_status_for_session_date(session_date: str) -> dict:
    session = datetime.fromisoformat(session_date).date()
    civil_starts_at, civil_ends_at = civil_recording_window(
        session,
        state.cfg.site.latitude,
        state.cfg.site.longitude,
        state.cfg.site.timezone,
    )
    nfc_starts_at, nfc_ends_at = astronomical_nfc_window(
        session,
        state.cfg.site.latitude,
        state.cfg.site.longitude,
        state.cfg.site.timezone,
    )
    return {
        "civil_starts_at": civil_starts_at.isoformat(timespec="seconds"),
        "civil_ends_at": civil_ends_at.isoformat(timespec="seconds"),
        "nfc_starts_at": nfc_starts_at.isoformat(timespec="seconds"),
        "nfc_ends_at": nfc_ends_at.isoformat(timespec="seconds"),
    }


def _status_defaults_for_existing_session(status: dict) -> dict:
    session_date = status.get("session_date")
    if not session_date:
        return _scheduled_window_status()

    defaults = {
        "session_date": session_date,
        "scheduled_starts_at": status.get("scheduled_starts_at"),
        "scheduled_ends_at": status.get("scheduled_ends_at"),
        "ends_at": status.get("ends_at") or status.get("scheduled_ends_at"),
    }
    defaults.update(_nfc_window_status_for_session_date(session_date))
    return defaults




def _resolve_session_log_path(session_date: str | None = None) -> Path | None:
    save_location = state.cfg.recording.save_location
    if session_date:
        return log_path_for_session_date(session_date, save_location)

    current = _current_status().get("session_date")
    if current:
        path = log_path_for_session_date(current, save_location)
        if path.exists():
            return path

    return latest_log_path(save_location)

def _current_status() -> dict:
    if state.session:
        status = state.session.status
        scheduled = _status_defaults_for_existing_session(status)
        for key in (
            "session_date",
            "scheduled_starts_at",
            "scheduled_ends_at",
            "ends_at",
            "civil_starts_at",
            "civil_ends_at",
            "nfc_starts_at",
            "nfc_ends_at",
        ):
            status.setdefault(key, scheduled.get(key))
        return status
    return _scheduled_window_status()


def _display_path(path: Path) -> str:
    try:
        return "~/" + str(path.expanduser().relative_to(Path.home()))
    except ValueError:
        return str(path)


FORMAT_PRESET_MAP_V24 = {
    "auto_native": (48000, 32),
    "float_48k": (48000, 32),
    "s16_48k": (48000, 16),
    "s16_441": (44100, 16),
    "s16_96k": (96000, 16),
    "float_96k": (96000, 32),
}


def _apply_recording_format_preset(cfg, preset: str) -> None:
    preset = preset or "auto_native"
    cfg.recording.format_preset = preset
    if preset in FORMAT_PRESET_MAP_V24:
        cfg.recording.sample_rate, cfg.recording.bit_depth = FORMAT_PRESET_MAP_V24[preset]


def _timezone_for_site(latitude: float, longitude: float, fallback: str) -> str:
    return config_mod.normalize_timezone(timezone_for_coordinates(latitude, longitude), fallback)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return RedirectResponse("/dashboard")


def _level_hint(peak_db) -> str:
    if peak_db is None:
        return "Couldn't read levels - try another device."
    if peak_db < -45:
        return "Very quiet. Move the mic, or check your gain."
    if peak_db > -3:
        return "Too loud - likely clipping. Lower the gain."
    return "Levels look good."


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "cfg": state.cfg.model_dump(),
            "status": _current_status(),
            "checks": [c.__dict__ for c in doctor.run_all()],
            "output_root_display": _display_path(recordings_root_path(state.cfg.recording.save_location)),
        },
    )


@router.post("/session/start")
async def session_start(force_now: str = Form(None)):
    if state.session is None or state.session.status.get("state") == "idle":
        state.session = Session(state.cfg, on_status=lambda s: state.broadcast({"type": "status", "data": s}))

    force = force_now in ("on", "true", "1", "yes")
    try:
        await stop_sounddevice_preview_meter()
        await state.session.start(force=force)
    except RuntimeError as e:
        return JSONResponse({"error": str(e), "status": _current_status()}, status_code=400)
    return JSONResponse(state.session.status)


@router.post("/session/stop")
async def session_stop():
    if state.session:
        await state.session.stop("user")
    return JSONResponse(_current_status())


@router.post("/session/analyze-pending")
async def session_analyze_pending(force: str = Form(None)):
    if not state.session:
        return JSONResponse({"error": "No session is available."}, status_code=400)
    started = state.session.start_pending_analysis(force=force in ("on", "true", "1", "yes"))
    if not started:
        return JSONResponse({"error": "No pending recordings are available for analysis.", "status": _current_status()}, status_code=400)
    return JSONResponse(_current_status())


@router.get("/session/status")
def session_status():
    return JSONResponse(_current_status())


@router.get("/session/log")
def session_log(session_date: str | None = None):
    path = _resolve_session_log_path(session_date)
    if not path or not path.exists():
        return JSONResponse({"rows": [], "path": None})
    return JSONResponse({"rows": read_log_rows(path, limit=1000), "path": str(path)})


@router.get("/session/log.csv")
def session_log_csv(session_date: str | None = None):
    path = _resolve_session_log_path(session_date)
    if not path or not path.exists():
        return JSONResponse({"error": "session log not found"}, status_code=404)
    session_name = path.parent.parent.name
    return FileResponse(path, media_type="text/csv", filename=f"nfc_session_log_{session_name}.csv")


@router.get("/api/mic-level")
async def api_mic_level(on_demand: bool = Query(False)):
    if state.session and state.session.status.get("state") == "recording":
        meter = state.session.status.get("meter") or {}
        level = meter.get("rms_db")
        if level is None:
            level = state.session.status.get("level_db")
        if level is None:
            level = meter.get("peak_db")
        return JSONResponse({
            "recording": True,
            "source": meter.get("source", "recording_backend"),
            "level_db": level,
            "rms_db": level,
            "peak_db": meter.get("peak_db", level),
            "rms": meter.get("rms"),
            "peak": meter.get("peak"),
            "near_full_scale_fraction": meter.get("near_full_scale_fraction", 0.0),
        })

    try:
        dev_id = state.cfg.recording.device
        dev = next((d for d in list_input_devices() if d["id"] == dev_id), None)
        if not dev:
            return JSONResponse({"error": "configured microphone not found"}, status_code=404)

        backend = str(getattr(state.cfg.recording, "backend", "auto") or "auto").lower()
        use_sounddevice = platform.system() == "Darwin" and backend in {"auto", "sounddevice", "coreaudio", "sounddevice_coreaudio"}
        if use_sounddevice:
            levels = await measure_sounddevice_preview_level(
                sample_rate=max(8000, int(getattr(state.cfg.recording, "sample_rate", 48000) or 48000)),
                channels=max(1, int(getattr(state.cfg.recording, "channels", 1) or 1)),
                selected_name=dev.get("name", ""),
            )
            level = levels.get("rms_db")
            return JSONResponse({
                **levels,
                "recording": False,
                "source": "sounddevice_coreaudio_preview",
                "level_db": level,
                "hint": _level_hint(level),
            })

        if not on_demand:
            return JSONResponse({
                "recording": False,
                "source": "ffmpeg_avfoundation_preview",
                "paused": True,
                "requires_on_demand": True,
                "level_db": None,
                "rms_db": None,
                "peak_db": None,
                "hint": "Meter preview is paused to save battery. Click the meter for a quick level check.",
            })

        levels = await measure_levels(dev["ffmpeg_input"], seconds=0.06)
        rms_db = levels.get("mean_db")
        peak_db = levels.get("peak_db")
        level = rms_db if rms_db is not None else peak_db
        return JSONResponse({
            **levels,
            "recording": False,
            "source": "ffmpeg_avfoundation_preview",
            "requires_on_demand": True,
            "level_db": level,
            "rms_db": level,
            "peak_db": peak_db if peak_db is not None else level,
            "hint": _level_hint(peak_db if peak_db is not None else level),
        })
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/mic-level/pause")
async def api_mic_level_pause():
    await stop_sounddevice_preview_meter()
    return JSONResponse({"ok": True})


@router.websocket("/ws/status")
async def ws_status(ws: WebSocket):
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=64)
    state.subscribers.add(q)
    try:
        await ws.send_json({"type": "status", "data": _current_status()})
        while True:
            payload = await q.get()
            await ws.send_json(payload)
    except Exception:
        pass
    finally:
        state.subscribers.discard(q)


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    schedule_preview = current_schedule_preview(state.cfg)
    install_status = installer.status()
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "cfg": state.cfg.model_dump(),
            "devices": list_input_devices(),
            "analyzers_status": install_status,
            "install_status": install_status,
            "schedule_mode": "twilight" if schedule_uses_twilight(state.cfg) else "manual",
            "schedule_presets": PRESETS,
            "schedule_preview": schedule_preview,
            "default_twilight_preset": DEFAULT_TWILIGHT_PRESET,
        },
    )


@router.post("/settings/choose-save-location")
async def settings_choose_save_location(request: Request):
    form = await request.form()
    current_path = str(form.get("current_save_location", state.cfg.recording.save_location) or "")

    try:
        selected = choose_directory(current_path, title="Choose where NFC Tools saves recordings")
    except FolderPickerUnavailable as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=503)

    if selected is None:
        return JSONResponse({"ok": False, "cancelled": True})

    return JSONResponse({"ok": True, "path": selected, "display": _display_path(Path(selected))})


@router.post("/settings/save")
async def settings_save(request: Request):
    form = await request.form()
    cfg = state.cfg
    cfg.site.name = form.get("site_name", cfg.site.name)
    cfg.site.latitude = float(form.get("latitude", cfg.site.latitude))
    cfg.site.longitude = float(form.get("longitude", cfg.site.longitude))
    cfg.site.timezone = _timezone_for_site(cfg.site.latitude, cfg.site.longitude, cfg.site.timezone)
    cfg.recording.device = form.get("device_id", cfg.recording.device)
    cfg.recording.save_location = str(form.get("save_location", cfg.recording.save_location) or "").strip()
    cfg.recording.backend = form.get("recording_backend", getattr(cfg.recording, "backend", "auto"))
    format_preset = form.get("format_preset", getattr(cfg.recording, "format_preset", "auto_native"))
    _apply_recording_format_preset(cfg, format_preset)
    cfg.power.sleep_prevention = form.get("sleep_prevention", cfg.power.sleep_prevention)
    cfg.power.analysis_policy = form.get("analysis_policy", cfg.power.analysis_policy)
    cfg.power.min_battery_percent_for_analysis = int(
        form.get("min_battery_percent_for_analysis", cfg.power.min_battery_percent_for_analysis)
    )
    cfg.power.low_battery_warning_percent = int(
        form.get("low_battery_warning_percent", cfg.power.low_battery_warning_percent)
    )
    cfg.power.critical_battery_percent = int(
        form.get("critical_battery_percent", cfg.power.critical_battery_percent)
    )
    cfg.power.critical_battery_action = form.get("critical_battery_action", cfg.power.critical_battery_action)
    if "sample_rate" in form:
        cfg.recording.sample_rate = int(form.get("sample_rate", cfg.recording.sample_rate))
    if "bit_depth" in form:
        cfg.recording.bit_depth = int(form.get("bit_depth", cfg.recording.bit_depth))
    schedule_mode = str(form.get("schedule_mode", "twilight" if schedule_uses_twilight(cfg) else "manual"))
    if schedule_mode == "twilight":
        cfg.schedule.mode = "twilight"
        cfg.schedule.auto_apply_preset = True
        cfg.schedule.preset = str(form.get("schedule_preset", cfg.schedule.preset or DEFAULT_TWILIGHT_PRESET))
        preview = current_schedule_preview(cfg)
        cfg.schedule.start_time = preview.start_time
        cfg.schedule.end_time = preview.end_time
    else:
        cfg.schedule.mode = "manual"
        cfg.schedule.auto_apply_preset = False
        cfg.schedule.preset = None
        cfg.schedule.start_time = form.get("start_time", cfg.schedule.start_time)
        cfg.schedule.end_time = form.get("end_time", cfg.schedule.end_time)
    cfg.schedule.segment_minutes = int(form.get("segment_minutes", cfg.schedule.segment_minutes))
    cfg.analyzers.birdnet_min_conf = float(form.get("birdnet_min_conf", cfg.analyzers.birdnet_min_conf))

    if hasattr(form, "getlist"):
        enabled = form.getlist("enabled_analyzers")
    else:
        enabled = (form.get("enabled_analyzers") or "").split(",")
    if enabled:
        cfg.analyzers.enabled = [e for e in enabled if e]

    config_mod.save(cfg)
    state.note_config_changed()
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/site-coordinates")
async def settings_site_coordinates(
    latitude: float = Form(...),
    longitude: float = Form(...),
):
    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return JSONResponse({"error": "invalid coordinates"}, status_code=400)

    cfg = state.cfg
    cfg.site.latitude = latitude
    cfg.site.longitude = longitude
    cfg.site.timezone = _timezone_for_site(latitude, longitude, cfg.site.timezone)
    config_mod.save(cfg)
    state.note_config_changed()
    return JSONResponse({
        "ok": True,
        "latitude": cfg.site.latitude,
        "longitude": cfg.site.longitude,
        "timezone": cfg.site.timezone,
    })


@router.post("/install/{name}")
def install_one(name: str, background: BackgroundTasks):
    installers = {
        "birdnet": installer.install_birdnet,
        "nighthawk": installer.install_nighthawk,
        "ffmpeg": installer.install_ffmpeg,
    }
    install_fn = installers.get(name)
    if install_fn is None:
        return JSONResponse({"error": "Unknown install target."}, status_code=404)

    log = state.install_log
    log.clear()
    state.install_active = name

    def cb(message, fraction):
        log.append(message)

    def run_install():
        try:
            install_fn(cb)
            log.append("Install finished successfully.")
        except Exception as e:  # noqa: BLE001
            log.append(f"Install did not finish: {e}")
        finally:
            state.install_active = None

    background.add_task(run_install)
    return JSONResponse({"queued": True})


@router.get("/install/log")
def install_log():
    return JSONResponse({"lines": list(state.install_log), "active": state.install_active})


@router.get("/install/status")
def install_status():
    return JSONResponse(installer.status())




@router.get("/api/sun-presets")
def api_sun_presets(lat: float, lon: float, tz: str):
    out = []
    for key, label, desc in PRESETS:
        try:
            start, end = preset_times(key, lat, lon, tz)
        except Exception:
            continue
        out.append(
            {
                "key": key,
                "label": label,
                "description": desc,
                "start_time": start,
                "end_time": end,
            }
        )
    return JSONResponse(out)
