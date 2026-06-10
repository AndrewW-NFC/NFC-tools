"""HTTP routes for the detection browser."""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates

from .. import detections as det
from ..paths import night_dir, recordings_root

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/detections", response_class=HTMLResponse)
def index(request: Request):
	nights = sorted([p.name for p in recordings_root().iterdir() if p.is_dir()], reverse=True)
	return templates.TemplateResponse("detections.html", {
		"request": request, "nights": nights,
		"selected": None, "rows": [], "summary": [],
		"filters": {"min_conf": 0.5, "analyzer": "", "species": ""},
	})


@router.get("/detections/{session_date}", response_class=HTMLResponse)
def for_night(request: Request, session_date: str,
			  min_conf: float = 0.5,
			  analyzer: Optional[str] = None,
			  species: Optional[str] = None):
	rows = det.collect_for_night(session_date, min_confidence=min_conf,
								 analyzer=analyzer or None, species=species or None)
	summary = det.species_summary(rows)
	nights = sorted([p.name for p in recordings_root().iterdir() if p.is_dir()], reverse=True)
	return templates.TemplateResponse("detections.html", {
		"request": request, "nights": nights, "selected": session_date,
		"rows": [r.to_dict() for r in rows], "summary": summary,
		"filters": {"min_conf": min_conf, "analyzer": analyzer or "", "species": species or ""},
	})


@router.get("/clip/{session_date}/{filename}")
def clip(session_date: str, filename: str, start: float = 0, end: float = 3):
	"""Return a short audio snippet around a detection."""
	import subprocess, tempfile
	from ..ffmpeg_locator import ensure_ffmpeg

	src = night_dir(session_date) / "audio" / filename
	if not src.exists():
		return JSONResponse({"error": "not found"}, status_code=404)

	pad = 0.5
	s = max(0.0, float(start) - pad)
	duration = max(0.5, float(end) - float(start) + 2 * pad)

	ffmpeg = ensure_ffmpeg()
	tmp = Path(tempfile.mkstemp(suffix=".wav")[1])
	try:
		subprocess.run(
			[ffmpeg, "-y", "-loglevel", "error",
			 "-ss", f"{s:.3f}", "-t", f"{duration:.3f}",
			 "-i", str(src), "-c", "copy", str(tmp)],
			check=True, timeout=20,
		)
		data = tmp.read_bytes()
		return Response(content=data, media_type="audio/wav")
	except Exception:
		return FileResponse(src, media_type="audio/wav")
	finally:
		try: tmp.unlink()
		except FileNotFoundError: pass


@router.get("/api/detections/{session_date}")
def api(session_date: str, min_conf: float = 0.0,
		analyzer: Optional[str] = None, species: Optional[str] = None):
	rows = det.collect_for_night(session_date, min_confidence=min_conf,
								 analyzer=analyzer or None, species=species or None)
	return JSONResponse({
		"session_date": session_date,
		"count": len(rows),
		"detections": [r.to_dict() for r in rows],
		"summary": det.species_summary(rows),
	})
