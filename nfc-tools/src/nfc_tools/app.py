"""Entry point for the GUI launcher: starts the web app and opens a browser."""
from __future__ import annotations
import threading
import time
import webbrowser

from . import config as config_mod
from .logging_setup import setup as setup_logging
from .web.server import run as run_web


def main() -> None:
	setup_logging()
	cfg = config_mod.load()
	url = f"http://{cfg.advanced.web_host}:{cfg.advanced.web_port}/"
	threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open(url)),
					 daemon=True).start()
	run_web()


if __name__ == "__main__":
	main()
