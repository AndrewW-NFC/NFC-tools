"""Auto-schedule UI routes."""
from __future__ import annotations
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .. import autoschedule
from ..config import load as load_cfg

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/schedule", response_class=HTMLResponse)
def page(request: Request):
	cfg = load_cfg()
	return templates.TemplateResponse("schedule.html", {
		"request": request, "cfg": cfg.model_dump(),
		"status": autoschedule.status().__dict__,
	})


@router.post("/schedule/enable")
def enable():
	cfg = load_cfg()
	autoschedule.install(cfg.schedule.start_time)
	return RedirectResponse("/schedule", status_code=303)


@router.post("/schedule/disable")
def disable():
	autoschedule.uninstall()
	return RedirectResponse("/schedule", status_code=303)
