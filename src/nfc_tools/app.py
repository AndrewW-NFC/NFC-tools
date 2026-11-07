"""Entry point for the GUI launcher: starts the web app and opens a browser."""

# Role: GUI command entry point that opens the local recorder interface.
# Dependencies: logging_setup initializes logs; web.server starts the HTTP service.
from __future__ import annotations

from .logging_setup import setup as setup_logging
from .web.server import run as run_web


def main() -> None:
    setup_logging()
    run_web(open_browser=True)


if __name__ == "__main__":
    main()
