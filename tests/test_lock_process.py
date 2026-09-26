"""Real-process regression tests for lock-owner liveness checks."""
import subprocess
import sys

import pytest

from nfc_tools.lock import FileLock, LockTimeout, _process_exists


@pytest.fixture
def live_process():
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
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


def test_process_exists_preserves_live_process(live_process):
    exists = _process_exists(live_process.pid)

    assert_process_still_running(live_process)
    assert exists is True


def test_file_lock_preserves_live_owner(tmp_path, live_process):
    lock_dir = tmp_path / ".analysis_lock"
    lock_dir.mkdir()
    pid_path = lock_dir / "pid"
    pid_path.write_text(str(live_process.pid))

    with pytest.raises(LockTimeout):
        with FileLock(lock_dir, timeout=0):
            pytest.fail("Acquired a lock owned by a live process")

    assert_process_still_running(live_process)
    assert pid_path.read_text() == str(live_process.pid)
