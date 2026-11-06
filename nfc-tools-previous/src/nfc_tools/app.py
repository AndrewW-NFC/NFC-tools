"""Entry point for the GUI launcher: starts the web app and opens a browser."""
from __future__ import annotations

from .logging_setup import setup as setup_logging
from .web.server import run as run_web


def main() -> None:
    setup_logging()
    run_web(open_browser=True)


if __name__ == "__main__":
    main()
