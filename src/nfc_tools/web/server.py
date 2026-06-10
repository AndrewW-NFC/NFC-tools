"""FastAPI app factory and uvicorn launcher."""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..config import load as load_cfg
from .routes import router
from .routes_detections import router as det_router
from .routes_export import router as export_router
from .routes_schedule import router as sched_router


def create_app() -> FastAPI:
	app = FastAPI(title="NFC Tools")
	static_dir = Path(__file__).parent / "static"
	app.mount("/static", StaticFiles(directory=static_dir), name="static")
	app.include_router(router)
	app.include_router(det_router)
	app.include_router(export_router)
	app.include_router(sched_router)
	return app


def run() -> None:
	import uvicorn
	cfg = load_cfg()
	uvicorn.run(create_app(), host=cfg.advanced.web_host, port=cfg.advanced.web_port,
				log_level="info")
