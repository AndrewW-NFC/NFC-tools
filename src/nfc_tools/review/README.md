# Human listening review

A separate local workspace for preparing batches, listening to recordings, and saving human annotations independently of detector predictions. Run `python -m nfc_tools.review --help` for `prepare`, `serve`, and `open` actions. Supply `--root` for the recording collection and `--batch` for the review batch.

`prepare.py` builds metadata/preview assets; `server.py` serves [static](static/README.md) and stores validated revisions in SQLite with backups. FastAPI, Pydantic, and Uvicorn provide the service; preparation uses NumPy and ffmpeg. Source audio remains separate from annotations.

## Files

| File | Purpose |
| --- | --- |
| [__init__.py](__init__.py) | Local, persistent recording review; independent of detector predictions. |
| [__main__.py](__main__.py) | Command-line launcher for the local listening-review workspace. |
| [prepare.py](prepare.py) | Prepare a deterministic, metadata-only pilot without modifying source audio. |
| [server.py](server.py) | Loopback-only review server with validated annotations and durable revisions. |
