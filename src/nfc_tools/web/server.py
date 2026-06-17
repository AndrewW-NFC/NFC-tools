"""FastAPI app factory and uvicorn launcher."""
from __future__ import annotations
from pathlib import Path
import threading
import time
import webbrowser

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..config import load as load_cfg
from .routes import router
from .routes_schedule import router as sched_router


def create_app() -> FastAPI:
    app = FastAPI(title="NFC Tools")
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.include_router(router)
    app.include_router(sched_router)
    return app


def browser_url(host: str, port: int) -> str:
    browser_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{browser_host}:{port}/"


def open_browser_soon(url: str, delay_seconds: float = 1.2) -> None:
    threading.Thread(
        target=lambda: (time.sleep(delay_seconds), webbrowser.open(url)),
        daemon=True,
    ).start()


def run(*, open_browser: bool = False) -> None:
    import uvicorn
    cfg = load_cfg()
    if open_browser:
        open_browser_soon(browser_url(cfg.advanced.web_host, cfg.advanced.web_port))
    uvicorn.run(create_app(), host=cfg.advanced.web_host, port=cfg.advanced.web_port,
                log_level="info")
