"""Real-process regression tests for lock-owner liveness checks."""
import subprocess
import sys
import time

import pytest

from nfc_tools.lock import FileLock, _process_exists


@pytest.fixture
def live_process(tmp_path):
    ready = tmp_path / "ready"
    process = subprocess.Popen([
        sys.executable,
        "-c",
        "import pathlib, sys, time; pathlib.Path(sys.argv[1]).touch(); time.sleep(60)",
        str(ready),
    ])
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "Dummy process did not finish starting"
        assert process.poll() is None
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def assert_process_still_running(process):
    # Termination can be asynchronous, so a single immediate poll is insufficient.
    with pytest.raises(subprocess.TimeoutExpired):
        process.wait(timeout=1)


def test_dummy_process_stays_alive_without_probe(live_process):
    assert_process_still_running(live_process)


def run_probe(code, *args):
    # On Windows, isolate console signals from pytest while exercising the real API.
    return subprocess.run(
        [sys.executable, "-c", code, *map(str, args)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_process_exists_preserves_live_process(live_process):
    result = run_probe(
        "import sys; from nfc_tools.lock import _process_exists; "
        "assert _process_exists(int(sys.argv[1])) is True",
        live_process.pid,
    )

    assert_process_still_running(live_process)
    assert result.returncode == 0, result.stderr


def test_file_lock_preserves_live_owner(tmp_path, live_process):
    lock_dir = tmp_path / ".analysis_lock"
    lock_dir.mkdir()
    pid_path = lock_dir / "pid"
    pid_path.write_text(str(live_process.pid))

    result = run_probe(
        "import sys\n"
        "from pathlib import Path\n"
        "from nfc_tools.lock import FileLock, LockTimeout\n"
        "try:\n"
        "    with FileLock(Path(sys.argv[1]), timeout=0):\n"
        "        raise AssertionError('Acquired a lock owned by a live process')\n"
        "except LockTimeout:\n"
        "    pass\n",
        lock_dir,
    )

    assert_process_still_running(live_process)
    assert result.returncode == 0, result.stderr
    assert pid_path.read_text() == str(live_process.pid)


def test_file_lock_recovers_exited_owner(tmp_path, live_process):
    live_process.terminate()
    live_process.wait(timeout=5)
    # Popen still holds its Windows process handle, so OpenProcess can succeed.
    assert _process_exists(live_process.pid) is False
    lock_dir = tmp_path / ".analysis_lock"
    lock_dir.mkdir()
    (lock_dir / "pid").write_text(str(live_process.pid))

    with FileLock(lock_dir, timeout=0):
        assert lock_dir.exists()

    assert not lock_dir.exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PID bounds")
@pytest.mark.parametrize("pid", [0, -1, 0x100000000])
def test_windows_invalid_pid_is_missing(pid):
    assert _process_exists(pid) is False
