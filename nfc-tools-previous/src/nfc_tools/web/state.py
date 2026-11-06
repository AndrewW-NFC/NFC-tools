"""Per-process app state (singleton-ish)."""
from __future__ import annotations
import asyncio
from typing import Optional, Set

from ..config import Config, load as load_cfg
from ..session import Session


class AppState:
    def __init__(self):
        self.cfg: Config = load_cfg()
        self.session: Optional[Session] = None
        self.subscribers: Set[asyncio.Queue] = set()
        self.install_log: list = []
        self.install_active: str | None = None
        self.config_revision: int = 0

    def broadcast(self, payload: dict) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    def note_config_changed(self) -> None:
        self.config_revision += 1


state = AppState()
