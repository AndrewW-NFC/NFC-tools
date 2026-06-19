"""Diagnostics HTTP routes and downloadable support artifacts."""
from __future__ import annotations

import io
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from .. import config as config_mod
from .. import doctor
from ..devices import list_input_devices
from ..paths import logs_dir, night_dir
from ..recorder import list_avfoundation_devices, record_test_clip_variant
from ..sounddevice_diagnostics import record_sounddevice_test
from .state import state

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()


def _recording_test_device_record() -> dict:
    dev_id = state.cfg.recording.device
    for device in list_input_devices():
        if device["id"] == dev_id:
            return device
    raise RuntimeError(f"Configured input device '{dev_id}' not found. Open Settings to choose a different mic.")


@router.post("/diagnostics/raw-recording-test")
async def diagnostics_raw_recording_test(request: Request):
    try:
        variant = request.query_params.get("variant", "current")
        allowed = {"current", "native_float", "float_48k", "s16_48k"}
        if variant not in allowed:
            return JSONResponse({"ok": False, "error": f"Unsupported raw-test variant: {variant}"}, status_code=400)

        device = _recording_test_device_record()
        session_date = datetime.now().date().isoformat()
        diag_dir = night_dir(session_date, state.cfg.recording.save_location) / "diagnostics"
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
    path = night_dir(session_date, state.cfg.recording.save_location) / "diagnostics" / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    media_type = "audio/wav" if filename.endswith(".wav") else "text/plain"
    return FileResponse(path, media_type=media_type, filename=filename)


@router.get("/diagnostics/avfoundation-devices")
async def diagnostics_avfoundation_devices():
    try:
        session_date = datetime.now().date().isoformat()
        diag_dir = night_dir(session_date, state.cfg.recording.save_location) / "diagnostics"
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
    path = night_dir(session_date, state.cfg.recording.save_location) / "diagnostics" / filename
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="text/plain", filename=filename)


@router.post("/diagnostics/sounddevice-raw-test")
async def diagnostics_sounddevice_raw_test():
    try:
        device = _recording_test_device_record()
        session_date = datetime.now().date().isoformat()
        diag_dir = night_dir(session_date, state.cfg.recording.save_location) / "diagnostics"
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
