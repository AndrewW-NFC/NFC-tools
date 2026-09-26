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
    if os.name == "nt":
        return _windows_process_exists(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _windows_process_exists(pid: int) -> bool:
    import ctypes
    from ctypes import wintypes

    # Windows PIDs are DWORDs; do not let ctypes wrap a malformed lock PID.
    if pid > 0xFFFFFFFF:
        return False
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE only.
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:  # ERROR_INVALID_PARAMETER: no such process.
            return False
        if error == 5:  # ERROR_ACCESS_DENIED: preserve the owner's lock.
            return True
        raise ctypes.WinError(error)
    try:
        result = kernel32.WaitForSingleObject(handle, 0)
        if result == 0:  # WAIT_OBJECT_0: process has exited (even if a handle remains).
            return False
        if result == 258:  # WAIT_TIMEOUT: process is still running.
            return True
        raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)
