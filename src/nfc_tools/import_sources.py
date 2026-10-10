"""Resolve explicit files and recursive folders into one import selection."""
from __future__ import annotations

import os
from pathlib import Path


def collect_sources(paths: list[str], extensions: set[str], on_error=None) -> tuple[Path, list[Path]]:
    selected = list(dict.fromkeys(Path(value).expanduser().resolve() for value in paths))
    if not selected:
        raise ValueError("Choose recording files or folders.")
    for path in selected:
        if not path.is_dir() and not (path.is_file() and path.suffix.lower() in extensions):
            raise ValueError(f"Choose an existing audio file or folder: {path}")
    root = Path(os.path.commonpath([str(p if p.is_dir() else p.parent) for p in selected]))
    files = set()

    def scan_error(error):
        if on_error:
            on_error(error)
        else:
            raise error

    for path in selected:
        if path.is_file():
            files.add(path)
            continue
        for directory, dirs, names in os.walk(path, onerror=scan_error, followlinks=False):
            dirs.sort()
            for name in sorted(names):
                candidate = Path(directory) / name
                if candidate.suffix.lower() in extensions:
                    files.add(candidate)
    return root, sorted(files)
