"""Night readiness HTTP routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..readiness import initial_readiness_groups, run_readiness_checks
from .state import state

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter()


@router.get("/readiness", response_class=HTMLResponse)
def readiness_page(request: Request):
    return templates.TemplateResponse(
        request,
        "readiness.html",
        {
            "groups": initial_readiness_groups(),
            "config_revision": state.config_revision,
        },
    )


@router.get("/readiness/state")
def readiness_state():
    return JSONResponse({"config_revision": state.config_revision})


@router.post("/readiness/run")
async def readiness_run():
    active_session_status = state.session.status if state.session else None
    groups = await run_readiness_checks(state.cfg, active_session_status)
    return JSONResponse({
        "config_revision": state.config_revision,
        "groups": groups,
    })
