"""Temporary macOS lid-sleep override, guarded by an independent root watchdog.

The privileged shell executes only fixed commands and quoted, generated paths.
Authorization is requested explicitly from Settings and lasts for the app process.
Analysis only requests leases from that already-authorized helper. It restores the
setting when the lease ends or the owning app exits. Multiple analyses in this
process share one lease; a root-owned lock excludes other apps.
"""

# Role: Provides the guarded macOS lease used by power management.
# Dependencies: macOS privileged shell commands, subprocesses, and a watchdog; no third-
# party Python imports.
from __future__ import annotations

import atexit
import json
import platform
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import threading
import time

_lock = threading.Lock()
_shared: MacLidLease | None = None
_authorization: MacLidAuthorization | None = None


def _watchdog_script(directory: Path, pid: int) -> str:
    lease = shlex.quote(str(directory))
    # Do not run Python or any other user-writable executable as administrator.
    return f"""set -eu
lease={lease}
lock=/var/run/nfc-tools-closed-lid.lock
/bin/test -d "$lease" || exit 1
/bin/kill -0 {int(pid)} || exit 1
/bin/mkdir "$lock" || exit 1
original=$(/usr/bin/pmset -g | /usr/bin/awk '$1 == "SleepDisabled" {{print $2}}')
case "$original" in
  0|1) ;;
  *) /bin/rmdir "$lock"; exit 1 ;;
esac
cleanup() {{
  restored=0
  /usr/bin/pmset disablesleep "$original" && /bin/rmdir "$lock" && restored=1
  /bin/rmdir "$lease/ready" 2>/dev/null || true
  /bin/test "$restored" = 1 || exit 1
}}
trap cleanup EXIT
trap 'exit 0' HUP INT TERM
/bin/test -d "$lease" || exit 1
/usr/bin/pmset disablesleep 1
/bin/mkdir "$lease/ready"
while /bin/test -d "$lease" && /bin/kill -0 {int(pid)} 2>/dev/null; do
  /bin/sleep 1
done
"""


def _authorization_script(directory: Path, pid: int) -> str:
    # Only fixed sleep-management commands run with elevation. Requests carry no
    # commands, executable paths, passwords, or caller-supplied process IDs.
    work = directory / "work"
    watchdog = _watchdog_script(work, pid)
    return f"""set -eu
control={shlex.quote(str(directory))}
/bin/test -d "$control" || exit 1
/bin/kill -0 {int(pid)} || exit 1
/bin/mkdir "$control/idle"
/bin/mkdir "$control/ready"
while /bin/test -d "$control" && /bin/kill -0 {int(pid)} 2>/dev/null; do
  if /bin/test -d "$control/work"; then
    /bin/rmdir "$control/idle"
    (
{watchdog}
    )
    /bin/mkdir "$control/idle"
  fi
  /bin/sleep 1
done
"""


class MacLidLease:
    def __init__(self):
        self.directory = Path(tempfile.mkdtemp(prefix="nfc-lid-"))
        self.process: subprocess.Popen | None = None
        self.users = 0

    @property
    def active(self) -> bool:
        return bool(self.process and self.process.poll() is None and (self.directory / "ready").is_dir())

    def start(self) -> None:
        authorization = _authorization
        if authorization is None or not authorization.active:
            raise RuntimeError(
                "Authorize closed-lid analysis in NFC Tools Settings → Power & battery "
                "before leaving the Mac unattended."
            )
        self.directory.rmdir()
        self.directory = authorization.directory / "work"
        self.authorization = authorization
        self.process = authorization.process
        self.directory.mkdir()
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.active:
                return
            if not authorization.active:
                break
            time.sleep(0.05)
        raise RuntimeError("The authorized sleep helper could not enable closed-lid analysis.")

    def _start_privileged(self, script: str) -> None:
        applescript = (
            "with timeout of 31536000 seconds\n"
            "do shell script " + json.dumps(script, ensure_ascii=False) + " with administrator privileges\n"
            "end timeout"
        )
        self.process = subprocess.Popen(
            ["/usr/bin/osascript", "-e", applescript],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.active:
                return
            if self.process.poll() is not None:
                raise RuntimeError("Administrator access was declined or macOS could not enable closed-lid analysis.")
            time.sleep(0.1)
        raise RuntimeError("Administrator approval timed out. Retry authorization in NFC Tools Settings.")

    def stop(self) -> bool:
        # Revoking the lease also prevents a late authorization from changing
        # settings. Never kill the privileged watchdog: it must run its trap.
        was_active = (self.directory / "ready").is_dir()
        revoked = self.directory.with_name(self.directory.name + ".revoked")
        try:
            # Atomic revocation avoids racing the watchdog's ready-directory
            # creation when authorization arrives just as startup times out.
            self.directory.rename(revoked)
        except FileNotFoundError:
            pass
        restored = True
        if getattr(self, "authorization", None) is not None:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if (self.authorization.directory / "idle").is_dir():
                    break
                if self.process.poll() is not None:
                    break
                time.sleep(0.05)
            restored = (
                self.authorization.active
                and (self.authorization.directory / "idle").is_dir()
            )
        elif self.process:
            try:
                result = self.process.wait(timeout=5)
                restored = result == 0 or not was_active
            except subprocess.TimeoutExpired:
                # A still-open authorization dialog may complete later. The
                # revoked lease makes its shell exit before changing settings.
                restored = not was_active
        for path in (revoked / "work" / "ready", revoked / "work",
                     revoked / "work.revoked" / "ready", revoked / "work.revoked",
                     revoked / "ready", revoked / "idle", revoked):
            try:
                path.rmdir()
            except FileNotFoundError:
                pass
        return restored


def acquire() -> MacLidLease:
    global _shared
    with _lock:
        if _shared is None or not _shared.active:
            if _shared is not None:
                _shared.stop()
            lease = MacLidLease()
            try:
                lease.start()
            except Exception:
                lease.stop()
                raise
            _shared = lease
        _shared.users += 1
        return _shared


def release(lease: MacLidLease) -> bool:
    global _shared
    with _lock:
        lease.users -= 1
        if lease.users == 0:
            restored = lease.stop()
            if _shared is lease:
                _shared = None
            return restored
        return True


class MacLidAuthorization(MacLidLease):
    """Explicitly approved helper, idle between analyses and gone at app exit."""

    def start(self) -> None:
        self._start_privileged(_authorization_script(self.directory, os.getpid()))


def authorization_status() -> dict:
    return {"supported": platform.system() == "Darwin",
            "authorized": bool(_authorization and _authorization.active)}


def authorize() -> dict:
    """Called only by an explicit user action, never by an analysis worker."""
    global _authorization
    if platform.system() != "Darwin":
        raise RuntimeError("This authorization is only needed on macOS.")
    with _lock:
        if _authorization is not None and _authorization.active:
            return authorization_status()
        if _authorization is not None:
            _authorization.stop()
        authorization = MacLidAuthorization()
        try:
            authorization.start()
        except Exception:
            authorization.stop()
            raise
        _authorization = authorization
        return authorization_status()


def shutdown() -> None:
    global _authorization, _shared
    with _lock:
        if _shared is not None:
            _shared.stop()
            _shared = None
        if _authorization is not None:
            _authorization.stop()
            _authorization = None


atexit.register(shutdown)
