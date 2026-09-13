"""Cross-platform serialization of analysis jobs via atomic mkdir."""
from __future__ import annotations
import os
import time
from pathlib import Path

from .logging_setup import get

log = get("lock")


class LockTimeout(Exception):
    pass


class FileLock:
    def __init__(self, path: Path, timeout: int = 3600, poll: float = 1.0):
        self.path = path
        self.timeout = timeout
        self.poll = poll

    def __enter__(self):
        waited = 0.0
        while True:
            try:
                self.path.mkdir(parents=False, exist_ok=False)
                (self.path / "pid").write_text(str(os.getpid()))
                return self
            except FileExistsError:
                if self._clear_stale_lock():
                    continue
                if waited >= self.timeout:
                    raise LockTimeout(f"Could not acquire lock at {self.path}")
                time.sleep(self.poll)
                waited += self.poll
                if int(waited) % 30 == 0:
                    log.info("waiting for lock at %s", self.path)

    def __exit__(self, *exc):
        try:
            for child in self.path.iterdir():
                child.unlink()
            self.path.rmdir()
        except FileNotFoundError:
            pass

    def _clear_stale_lock(self) -> bool:
        pid_path = self.path / "pid"
        try:
            raw_pid = pid_path.read_text().strip()
            pid = int(raw_pid)
        except (FileNotFoundError, ValueError):
            return False

        if _process_exists(pid):
            return False

        try:
            for child in self.path.iterdir():
                child.unlink()
            self.path.rmdir()
            log.warning("removed stale analysis lock at %s for exited pid %s", self.path, pid)
            return True
        except OSError as e:
            log.warning("could not remove stale analysis lock at %s: %s", self.path, e)
            return False


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True
