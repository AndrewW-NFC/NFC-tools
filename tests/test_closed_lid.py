import os
import shlex
import subprocess
import time

import pytest

from nfc_tools import closed_lid


@pytest.mark.skipif(os.name != "posix", reason="macOS watchdog uses a POSIX shell")
@pytest.mark.parametrize("original", ["0", "1"])
@pytest.mark.parametrize("end", ["finish", "crash", "failure", "restore_failure"])
def test_watchdog_restores_previous_setting(tmp_path, original, end):
    lease = tmp_path / "lease with 'quotes'"
    lease.mkdir()
    lock = tmp_path / "lock"
    state = tmp_path / "state"
    state.write_text(original)
    fake_pmset = tmp_path / "pmset"
    fake_pmset.write_text(
        '#!/bin/sh\n'
        f'state={shlex.quote(str(state))}\n'
        'if [ "$1" = "-g" ]; then printf " SleepDisabled %s\\n" "$(cat "$state")"; '
        'else printf "%s" "$2" > "$state"; fi\n'
    )
    if end == "restore_failure":
        fake_pmset.write_text(fake_pmset.read_text().replace(
            'else printf', f'elif [ -d {shlex.quote(str(lock))} ] && [ ! -d {shlex.quote(str(lease))} ]; then exit 9; else printf'
        ))
    fake_pmset.chmod(0o755)
    owner = subprocess.Popen(["/bin/sleep", "60"])
    script = closed_lid._watchdog_script(lease, owner.pid)
    script = script.replace("/usr/bin/pmset", shlex.quote(str(fake_pmset)))
    script = script.replace("/var/run/nfc-tools-closed-lid.lock", shlex.quote(str(lock)))
    script = script.replace("/bin/sleep 1", "/bin/sleep 0.02")
    if end == "failure":
        script = script.replace('/bin/mkdir "$lease/ready"', 'exit 42')
    proc = subprocess.Popen(["/bin/sh", "-c", script])
    try:
        if end != "failure":
            deadline = time.monotonic() + 5
            while not (lease / "ready").exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert (lease / "ready").exists()
            assert state.read_text() == "1"
            assert lock.is_dir()
            if end in {"finish", "restore_failure"}:
                handle = closed_lid.MacLidLease.__new__(closed_lid.MacLidLease)
                handle.directory = lease
                handle.process = proc
                assert handle.stop() is (end == "finish")
                assert not lease.with_name(lease.name + ".revoked").exists()
            else:
                owner.terminate()
                owner.wait(timeout=5)
        proc.wait(timeout=5)
        assert proc.returncode == (42 if end == "failure" else 1 if end == "restore_failure" else 0)
        assert state.read_text() == ("1" if end == "restore_failure" else original)
        assert lock.exists() is (end == "restore_failure")
        assert not (lease / "ready").exists()
    finally:
        owner.terminate()
        owner.wait(timeout=5)
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)


def test_overlapping_analyses_share_lease(monkeypatch):
    events = []

    class Lease:
        active = True
        users = 0

        def start(self):
            events.append("start")

        def stop(self):
            events.append("stop")
            return True

    monkeypatch.setattr(closed_lid, "_shared", None)
    monkeypatch.setattr(closed_lid, "MacLidLease", Lease)
    first = closed_lid.acquire()
    second = closed_lid.acquire()
    assert first is second
    closed_lid.release(first)
    assert events == ["start"]
    closed_lid.release(second)
    assert events == ["start", "stop"]
    assert closed_lid._shared is None


def test_failed_authorization_revokes_lease(monkeypatch):
    events = []

    class Lease:
        def start(self):
            raise RuntimeError("declined")

        def stop(self):
            events.append("stop")
            return True

    monkeypatch.setattr(closed_lid, "_shared", None)
    monkeypatch.setattr(closed_lid, "MacLidLease", Lease)
    with pytest.raises(RuntimeError, match="declined"):
        closed_lid.acquire()
    assert events == ["stop"]
    assert closed_lid._shared is None


def test_pending_authorization_cannot_enable_revoked_lease(monkeypatch):
    class Pending:
        def wait(self, timeout):
            raise subprocess.TimeoutExpired("osascript", timeout)

    lease = closed_lid.MacLidLease()
    lease.process = Pending()
    lease.stop()
    assert not lease.directory.exists()
    script = closed_lid._watchdog_script(lease.directory, os.getpid())
    assert script.index('/bin/test -d "$lease"') < script.index('/usr/bin/pmset disablesleep 1')
