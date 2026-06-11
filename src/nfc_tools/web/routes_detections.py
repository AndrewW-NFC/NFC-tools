"""HTTP routes for the detection browser."""

from __future__ import annotations

import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

from .. import detections as det
from ..ffmpeg_locator import ensure_ffmpeg
from ..paths import night_dir

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _include_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def _preview_payload(folder_path: str, include_subfolders: bool) -> dict:
    folders = det.find_detection_folders(folder_path, include_subfolders=include_subfolders)
    return {
        "folder_path": folder_path,
        "include_subfolders": include_subfolders,
        "folders": [str(p) for p in folders],
        "preview_folders": [str(p) for p in folders[:10]],
        "folder_count": len(folders),
    }



@router.get("/detections/pick-folder")
def pick_detection_folder():
    """Open a native macOS folder picker and return the selected path."""
    if sys.platform != "darwin":
        return JSONResponse(
            {
                "error": "Folder browsing is currently available only on macOS in this local build.",
                "detail": "The browser cannot safely provide local folder paths directly.",
            },
            status_code=501,
        )
    script = 'POSIX path of (choose folder with prompt "Choose a folder containing NFC Tools detections")'

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return JSONResponse({"folder_path": ""})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(
            {"error": "Could not open the folder picker.", "detail": str(e)},
            status_code=500,
        )

    if result.returncode != 0:
        if "User canceled" in result.stderr or "(-128)" in result.stderr:
            return JSONResponse({"folder_path": ""})
        return JSONResponse(
            {"error": "Could not open the folder picker.", "detail": result.stderr.strip() or result.stdout.strip()},
            status_code=500,
        )

    return JSONResponse({"folder_path": result.stdout.strip()})


@router.get("/detections", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request,
        "detections.html",
        {
            "mode": "select",
            "folder_path": "",
            "include_subfolders": False,
            "preview_folders": [],
            "folder_count": 0,
            "selected_folders": [],
            "rows": [],
            "summary": [],
            "filters": {"min_conf": 0.5, "analyzer": "", "species": ""},
            "error": "",
        },
    )


@router.post("/detections/preview", response_class=HTMLResponse)
def preview(
    request: Request,
    folder_path: str = Form(...),
    include_subfolders: Optional[str] = Form(None),
):
    include = _include_bool(include_subfolders)
    payload = _preview_payload(folder_path, include)

    error = ""
    if not Path(folder_path).expanduser().exists():
        error = "That folder path does not exist."
    elif payload["folder_count"] == 0:
        error = "No NFC Tools detection folders were found at that path."

    return templates.TemplateResponse(
        request,
        "detections.html",
        {
            "mode": "preview",
            **payload,
            "selected_folders": [],
            "rows": [],
            "summary": [],
            "filters": {"min_conf": 0.5, "analyzer": "", "species": ""},
            "error": error,
        },
    )


@router.get("/detections/browse", response_class=HTMLResponse)
def browse(
    request: Request,
    folder_path: str = Query(...),
    include_subfolders: bool = Query(False),
    min_conf: float = Query(0.5),
    analyzer: Optional[str] = Query(None),
    species: Optional[str] = Query(None),
):
    include = _include_bool(include_subfolders)
    payload = _preview_payload(folder_path, include)

    rows = []
    detections_for_summary = []

    for folder in payload["folders"]:
        folder_rows = det.collect_for_folder(
            folder,
            min_confidence=min_conf,
            analyzer=analyzer or None,
            species=species or None,
        )
        detections_for_summary.extend(folder_rows)

        for d in folder_rows:
            item = d.to_dict()
            item["folder_path"] = folder
            item["audio_path"] = str(Path(folder) / "audio" / d.filename)
            item["clip_url"] = (
                "/clip-file"
                f"?audio_path={quote(item['audio_path'])}"
                f"&start={d.start_seconds:.3f}"
                f"&end={d.end_seconds:.3f}"
            )
            rows.append(item)

    rows.sort(key=lambda r: (r.get("timestamp") or "", r.get("folder_path") or "", r.get("filename") or ""))

    return templates.TemplateResponse(
        request,
        "detections.html",
        {
            "mode": "browse",
            **payload,
            "selected_folders": payload["folders"],
            "rows": rows,
            "summary": det.species_summary(detections_for_summary),
            "filters": {"min_conf": min_conf, "analyzer": analyzer or "", "species": species or ""},
            "error": "",
        },
    )


@router.get("/clip-file")
def clip_file(audio_path: str, start: float = 0, end: float = 3):
    """Return a short audio snippet around a detection from an explicit audio path."""
    src = Path(audio_path).expanduser().resolve()

    if not src.exists() or not src.is_file() or src.suffix.lower() != ".wav":
        return JSONResponse({"error": "audio file not found"}, status_code=404)

    pad = 0.5
    s = max(0.0, float(start) - pad)
    duration = max(0.5, float(end) - float(start) + 2 * pad)

    ffmpeg = ensure_ffmpeg()
    tmp = Path(tempfile.mkstemp(suffix=".wav")[1])

    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-ss",
                f"{s:.3f}",
                "-t",
                f"{duration:.3f}",
                "-i",
                str(src),
                "-c",
                "copy",
                str(tmp),
            ],
            check=True,
            timeout=20,
        )
        data = tmp.read_bytes()
        return Response(content=data, media_type="audio/wav")
    except Exception:
        return FileResponse(src, media_type="audio/wav")
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


# Legacy routes kept for compatibility with old links/API behavior.

@router.get("/detections/{session_date}", response_class=HTMLResponse)
def for_night(
    request: Request,
    session_date: str,
    min_conf: float = 0.5,
    analyzer: Optional[str] = None,
    species: Optional[str] = None,
):
    nd = night_dir(session_date)
    return browse(
        request,
        folder_path=str(nd),
        include_subfolders=False,
        min_conf=min_conf,
        analyzer=analyzer,
        species=species,
    )


@router.get("/clip/{session_date}/{filename}")
def clip(session_date: str, filename: str, start: float = 0, end: float = 3):
    src = night_dir(session_date) / "audio" / filename
    return clip_file(str(src), start=start, end=end)


@router.get("/api/detections/{session_date}")
def api(
    session_date: str,
    min_conf: float = 0.0,
    analyzer: Optional[str] = None,
    species: Optional[str] = None,
):
    rows = det.collect_for_night(
        session_date,
        min_confidence=min_conf,
        analyzer=analyzer or None,
        species=species or None,
    )
    return JSONResponse(
        {
            "session_date": session_date,
            "count": len(rows),
            "detections": [r.to_dict() for r in rows],
            "summary": det.species_summary(rows),
        }
    )
