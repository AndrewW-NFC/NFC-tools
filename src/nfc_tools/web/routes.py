"""Main HTTP routes (wizard, dashboard, results, settings, diagnostics)."""

from __future__ import annotations

import asyncio
import platform
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, Request, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .. import config as config_mod
from .. import doctor, installer, manifest
from ..devices import list_input_devices
from ..ephemeris import PRESETS, preset_times
from ..paths import logs_dir, night_dir, recordings_root
from ..recorder import list_avfoundation_devices, measure_levels, record_test_clip_variant
from ..sounddevice_diagnostics import measure_sounddevice_preview_level, record_sounddevice_test
from ..scheduler import compute_window
from ..session import Session
from ..session_logging import latest_log_path, log_path_for_session_date, read_log_rows
from .geocode import lookup as geocode_lookup
from .state import state

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()



def _normalize_evening_start(win):
    """Treat morning-looking dusk starts as PM for overnight NFC sessions."""
    if (
        win.starts_at.hour < 12
        and win.ends_at.date() > win.starts_at.date()
        and win.ends_at.hour < 12
    ):
        win.starts_at = win.starts_at + timedelta(hours=12)
    return win


def _scheduled_window_status() -> dict:
    now = datetime.now()
    win = compute_window(now, state.cfg.schedule.start_time, state.cfg.schedule.end_time)
    win = _normalize_evening_start(win)
    if now >= win.ends_at:
        win = compute_window(now + timedelta(hours=12), state.cfg.schedule.start_time, state.cfg.schedule.end_time)
        win = _normalize_evening_start(win)

    return {
        "state": "idle",
        "session_date": win.session_date.isoformat(),
        "scheduled_starts_at": win.starts_at.isoformat(timespec="seconds"),
        "scheduled_ends_at": win.ends_at.isoformat(timespec="seconds"),
        "ends_at": win.ends_at.isoformat(timespec="seconds"),
        "recordings": [],
        "level_db": None,
    }




def _resolve_session_log_path(session_date: str | None = None) -> Path | None:
    if session_date:
        return log_path_for_session_date(session_date)

    current = _current_status().get("session_date")
    if current:
        path = log_path_for_session_date(current)
        if path.exists():
            return path

    return latest_log_path()

def _current_status() -> dict:
    if state.session:
        status = state.session.status
        scheduled = _scheduled_window_status()
        for key in ("session_date", "scheduled_starts_at", "scheduled_ends_at", "ends_at"):
            status.setdefault(key, scheduled.get(key))
        return status
    return _scheduled_window_status()



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


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    if not state.cfg.first_run_complete:
        return RedirectResponse("/wizard")
    return RedirectResponse("/dashboard")


@router.get("/wizard", response_class=HTMLResponse)
def wizard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "wizard.html",
        {
            "cfg": state.cfg.model_dump(),
            "devices": list_input_devices(),
            "analyzers_status": installer.status(),
        },
    )


@router.post("/wizard/geocode")
def wizard_geocode(query: str = Form(...)):
    return JSONResponse(geocode_lookup(query) or {"error": "not found"})


@router.post("/wizard/test-mic")
async def wizard_test_mic(device_id: str = Form(...)):
    devs = {d["id"]: d for d in list_input_devices()}
    d = devs.get(device_id)
    if not d:
        return JSONResponse({"error": "device not found"}, status_code=400)
    levels = await measure_levels(d["ffmpeg_input"], seconds=4)
    hint = _level_hint(levels.get("peak_db"))
    return JSONResponse({**levels, "hint": hint})




def _recording_test_device_record() -> dict:
    dev_id = state.cfg.recording.device
    for d in list_input_devices():
        if d["id"] == dev_id:
            return d
    raise RuntimeError(f"Configured input device '{dev_id}' not found. Open Settings to choose a different mic.")

def _level_hint(peak_db) -> str:
    if peak_db is None:
        return "Couldn't read levels - try another device."
    if peak_db < -45:
        return "Very quiet. Move the mic, or check your gain."
    if peak_db > -3:
        return "Too loud - likely clipping. Lower the gain."
    return "Levels look good."


@router.post("/wizard/save")
def wizard_save(
    site_name: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timezone: str | None = Form(None),
    device_id: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    install_birdnet: str = Form("on"),
    install_nighthawk: str = Form("on"),
    background: BackgroundTasks = None,  # type: ignore[assignment]
):
    cfg = state.cfg
    cfg.site.name = site_name
    cfg.site.latitude = latitude
    cfg.site.longitude = longitude
    cfg.site.timezone = timezone or cfg.site.timezone
    cfg.recording.device = device_id
    cfg.schedule.start_time = start_time
    cfg.schedule.end_time = end_time

    enabled = []
    if install_birdnet == "on":
        enabled.append("birdnet")
    if install_nighthawk == "on":
        enabled.append("nighthawk")
    cfg.analyzers.enabled = enabled or ["birdnet"]
    cfg.first_run_complete = True
    config_mod.save(cfg)

    if background:
        if "birdnet" in enabled:
            background.add_task(installer.install_birdnet, lambda m, f: state.install_log.append(m))
        if "nighthawk" in enabled:
            background.add_task(installer.install_nighthawk, lambda m, f: state.install_log.append(m))

    return RedirectResponse("/dashboard", status_code=303)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "cfg": state.cfg.model_dump(),
            "status": _current_status(),
            "checks": [c.__dict__ for c in doctor.run_all()],
        },
    )


@router.post("/session/start")
async def session_start(force_now: str = Form(None)):
    if state.session is None or state.session.status.get("state") == "idle":
        state.session = Session(state.cfg, on_status=lambda s: state.broadcast({"type": "status", "data": s}))

    force = force_now in ("on", "true", "1", "yes")
    try:
        await state.session.start(force=force)
    except RuntimeError as e:
        return JSONResponse({"error": str(e), "status": _current_status()}, status_code=400)
    return JSONResponse(state.session.status)


@router.post("/session/stop")
async def session_stop():
    if state.session:
        await state.session.stop("user")
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
async def api_mic_level():
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

        levels = await measure_levels(dev["ffmpeg_input"], seconds=0.06)
        rms_db = levels.get("mean_db")
        peak_db = levels.get("peak_db")
        level = rms_db if rms_db is not None else peak_db
        return JSONResponse({
            **levels,
            "recording": False,
            "source": "ffmpeg_avfoundation_preview",
            "level_db": level,
            "rms_db": level,
            "peak_db": peak_db if peak_db is not None else level,
            "hint": _level_hint(peak_db if peak_db is not None else level),
        })
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"error": str(e)}, status_code=500)


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


@router.get("/results", response_class=HTMLResponse)
def results_index(request: Request):
    nights = sorted([p.name for p in recordings_root().iterdir() if p.is_dir()], reverse=True)
    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "nights": nights,
            "selected": None,
            "rows": [],
        },
    )


@router.get("/results/{session_date}", response_class=HTMLResponse)
def results_for(request: Request, session_date: str):
    nd = night_dir(session_date)
    rows = manifest.read_all(nd)
    nights = sorted([p.name for p in recordings_root().iterdir() if p.is_dir()], reverse=True)
    return templates.TemplateResponse(
        request,
        "results.html",
        {
            "nights": nights,
            "selected": session_date,
            "rows": rows,
        },
    )


@router.get("/audio/{session_date}/{filename}")
def get_audio(session_date: str, filename: str):
    path = night_dir(session_date) / "audio" / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="audio/wav")


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "cfg": state.cfg.model_dump(),
            "devices": list_input_devices(),
            "analyzers_status": installer.status(),
        },
    )


@router.post("/settings/save")
async def settings_save(request: Request):
    form = await request.form()
    cfg = state.cfg
    cfg.site.name = form.get("site_name", cfg.site.name)
    cfg.site.latitude = float(form.get("latitude", cfg.site.latitude))
    cfg.site.longitude = float(form.get("longitude", cfg.site.longitude))
    cfg.site.timezone = form.get("timezone") or cfg.site.timezone
    cfg.recording.device = form.get("device_id", cfg.recording.device)
    cfg.recording.backend = form.get("recording_backend", getattr(cfg.recording, "backend", "auto"))
    format_preset = form.get("format_preset", getattr(cfg.recording, "format_preset", "auto_native"))
    _apply_recording_format_preset(cfg, format_preset)
    if "sample_rate" in form:
        cfg.recording.sample_rate = int(form.get("sample_rate", cfg.recording.sample_rate))
    if "bit_depth" in form:
        cfg.recording.bit_depth = int(form.get("bit_depth", cfg.recording.bit_depth))
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
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/site-coordinates")
async def settings_site_coordinates(
    latitude: float = Form(...),
    longitude: float = Form(...),
    timezone: str | None = Form(None),
):
    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return JSONResponse({"error": "invalid coordinates"}, status_code=400)

    cfg = state.cfg
    cfg.site.latitude = latitude
    cfg.site.longitude = longitude
    if timezone:
        cfg.site.timezone = timezone
    config_mod.save(cfg)
    return JSONResponse({"ok": True, "latitude": cfg.site.latitude, "longitude": cfg.site.longitude})


@router.post("/install/{name}")
def install_one(name: str, background: BackgroundTasks):
    log = state.install_log
    log.clear()

    def cb(message, fraction):
        log.append(message)

    if name == "birdnet":
        background.add_task(installer.install_birdnet, cb)
    elif name == "nighthawk":
        background.add_task(installer.install_nighthawk, cb)
    elif name == "ffmpeg":
        background.add_task(installer.install_ffmpeg, cb)

    return JSONResponse({"queued": True})


@router.get("/install/log")
def install_log():
    return JSONResponse({"lines": list(state.install_log)})




@router.post("/diagnostics/raw-recording-test")
async def diagnostics_raw_recording_test(request: Request):
    try:
        variant = request.query_params.get("variant", "current")
        allowed = {"current", "native_float", "float_48k", "s16_48k"}
        if variant not in allowed:
            return JSONResponse({"ok": False, "error": f"Unsupported raw-test variant: {variant}"}, status_code=400)

        device = _recording_test_device_record()
        session_date = datetime.now().date().isoformat()
        diag_dir = night_dir(session_date) / "diagnostics"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        wav_path = diag_dir / f"raw_test_{stamp}_{variant}.wav"
        metadata = {
            "configured_device_id": state.cfg.recording.device,
            "selected_device_id": device.get("id", ""),
            "selected_device_name": device.get("name", ""),
            "ffmpeg_input": device.get("ffmpeg_input", []),
            "sample_rate": state.cfg.recording.sample_rate,
            "channels": state.cfg.recording.channels,
            "bit_depth": state.cfg.recording.bit_depth,
            "site_name": state.cfg.site.name,
            "variant": variant,
        }
        result = await record_test_clip_variant(
            device["ffmpeg_input"],
            wav_path,
            variant=variant,
            seconds=10,
            sample_rate=state.cfg.recording.sample_rate,
            channels=state.cfg.recording.channels,
            bit_depth=state.cfg.recording.bit_depth,
            diagnostics_metadata=metadata,
        )
        result["device"] = metadata
        result["download_url"] = f"/diagnostics/raw-recording-test/{session_date}/{result['wav_name']}"
        result["log_download_url"] = f"/diagnostics/raw-recording-test/{session_date}/{result['log_name']}"
        return JSONResponse(result)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/diagnostics/raw-recording-test/{session_date}/{filename}")
def diagnostics_raw_recording_file(session_date: str, filename: str):
    if "/" in filename or ".." in filename:
        return JSONResponse({"error": "invalid filename"}, status_code=400)
    path = night_dir(session_date) / "diagnostics" / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    media_type = "audio/wav" if filename.endswith(".wav") else "text/plain"
    return FileResponse(path, media_type=media_type, filename=filename)




@router.get("/diagnostics/avfoundation-devices")
async def diagnostics_avfoundation_devices():
    try:
        session_date = datetime.now().date().isoformat()
        diag_dir = night_dir(session_date) / "diagnostics"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = diag_dir / f"avfoundation_devices_{stamp}.log"
        result = await list_avfoundation_devices(log_path=log_path)
        result["download_url"] = f"/diagnostics/avfoundation-devices/{session_date}/{log_path.name}"
        return JSONResponse(result)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/diagnostics/avfoundation-devices/{session_date}/{filename}")
def diagnostics_avfoundation_devices_file(session_date: str, filename: str):
    if "/" in filename or ".." in filename:
        return JSONResponse({"error": "invalid filename"}, status_code=400)
    path = night_dir(session_date) / "diagnostics" / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="text/plain", filename=filename)




@router.post("/diagnostics/sounddevice-raw-test")
async def diagnostics_sounddevice_raw_test():
    try:
        device = _recording_test_device_record()
        session_date = datetime.now().date().isoformat()
        diag_dir = night_dir(session_date) / "diagnostics"
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        wav_path = diag_dir / f"raw_test_{stamp}_sounddevice_coreaudio_float_48k.wav"
        result = await record_sounddevice_test(
            wav_path,
            seconds=10,
            sample_rate=48000,
            channels=1,
            selected_name=device.get("name", ""),
        )
        result["device"] = {
            "configured_device_id": state.cfg.recording.device,
            "selected_device_id": device.get("id", ""),
            "selected_device_name": device.get("name", ""),
            "site_name": state.cfg.site.name,
        }
        result["download_url"] = f"/diagnostics/raw-recording-test/{session_date}/{result['wav_name']}"
        result["log_download_url"] = f"/diagnostics/raw-recording-test/{session_date}/{result['log_name']}"
        return JSONResponse(result, status_code=200 if result.get("ok") else 500)
    except Exception as e:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/diagnostics", response_class=HTMLResponse)
def diagnostics_page(request: Request):
    return templates.TemplateResponse(
        request,
        "diagnostics.html",
        {
            "checks": [c.__dict__ for c in doctor.run_all()],
        },
    )


@router.get("/diagnostics/bundle")
def diagnostics_bundle():
    import io

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for log in logs_dir().glob("*.log*"):
            zf.write(log, arcname=f"logs/{log.name}")

        cfg_path = config_mod.CONFIG_PATH
        if cfg_path.exists():
            zf.writestr("config.yaml", cfg_path.read_text())

        zf.writestr(
            "doctor.txt",
            "\n".join(
                f"{c.name}: {'OK' if c.ok else 'FAIL'} - {c.detail} ({c.fix_hint})"
                for c in doctor.run_all()
            ),
        )

    buf.seek(0)
    fname = f"nfc-diagnostics-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


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
