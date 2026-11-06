"""Night coverage and explicitly requested recovery of saved recordings."""
from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates

from .. import night_status
from .. import precipitation
from ..importer import manager
from ..paths import recordings_root_path
from ..session import Session
from .state import state

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
_guard = threading.Lock()
_job = {"active": False, "message": "", "night": None}


def recovery_active():
    return _job["active"]


def night_path(value):
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError()
    except ValueError:
        raise HTTPException(400, "Choose a night in YYYY-MM-DD format.")
    root = recordings_root_path(state.cfg.recording.save_location).resolve()
    path = root / value
    if not path.is_dir() or path.resolve().parent != root:
        raise HTTPException(404, "Night folder was not found.")
    return path


def busy():
    session = state.session
    return bool(manager.active() or (session and (
        session.status.get("state") != "idle" or
        session.status.get("analysis", {}).get("active") or
        getattr(session, "_analysis_drain_running", False))))


@router.get("/nights")
def page(request: Request):
    root = recordings_root_path(state.cfg.recording.save_location)
    nights = []
    if root.exists():
        for path in sorted(root.iterdir(), reverse=True):
            try:
                date.fromisoformat(path.name)
                if path.is_dir() and ((path / "audio").exists() or (path / "logs").exists()):
                    nights.append(path.name)
            except ValueError:
                pass
    return templates.TemplateResponse(request=request, name="nights.html", context={"nights": nights})


@router.get("/api/nights/{night}")
def report(night: str):
    path = night_path(night)
    try:
        report = night_status.summarize(path, state.cfg)
        report["busy"] = busy() or recovery_active()
        report["recovery"] = dict(_job)
        report["precipitation"] = precipitation.saved_summary(path)
        return report
    except (ValueError, OSError) as exc:
        raise HTTPException(409, f"Could not read night progress: {exc}") from exc


@router.post("/api/nights/{night}/precipitation")
def refresh_precipitation(night: str):
    path = night_path(night)
    try:
        return precipitation.refresh_night(path)
    except Exception as exc:
        raise HTTPException(502, f"Precipitation could not be refreshed; previous report retained: {exc}") from exc


def recover(path, cfg):
    session = Session(cfg)
    session._status["session_date"] = path.name
    session._prepare_session_log(path)
    try:
        allowed, message, _ = session._analysis_power_decision()
        if not allowed:
            raise RuntimeError(message)
        session._start_sleep_prevention("analysis")
        report = night_status.summarize(path, cfg)
        for item in report["files"]:
            if item["pending"]:
                _job["message"] = f"Recovering {item['filename']}"
                session._analyze_one(path / "audio" / item["filename"], resume=True)
        session._refresh_ebird_exports(path)
        report = night_status.summarize(path, cfg)
        _job["message"] = (f"Recovery finished: {report['pending_files']} recording(s) still need analysis or clip export; "
                           f"{report['invalid_files']} unreadable recording(s). eBird exports: {report['exports']['status']}.")
    except Exception as exc:  # noqa: BLE001
        _job["message"] = f"Recovery stopped: {exc}. Saved progress is retained; retry after resolving the problem."
    finally:
        try:
            session._release_sleep_prevention()
        finally:
            session._pool.shutdown(wait=False)
            _job["active"] = False


@router.post("/api/nights/{night}/recover")
async def start_recovery(night: str):
    path = night_path(night)
    with _guard:
        if recovery_active() or busy():
            raise HTTPException(409, "Wait for recording, analysis, or imports to finish before recovering a night.")
        _job.update(active=True, night=night, message="Checking saved recordings…")
        threading.Thread(target=recover, args=(path, state.cfg.model_copy(deep=True)), daemon=True).start()
    return dict(_job)
