"""Regression tests for power."""

# Role: Run by pytest to protect the behavior exercised by the tests below.
# Dependencies: pytest runs the tests. Project/external imports: nfc_tools.power.

from nfc_tools import power
from nfc_tools.power import SleepPreventer, current_power_snapshot


def test_macos_power_snapshot_parses_battery(monkeypatch):
    monkeypatch.setattr(power.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(
        power.subprocess,
        "check_output",
        lambda *args, **kwargs: "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1234567)\t82%; discharging; 4:12 remaining present: true",
    )

    snapshot = current_power_snapshot()

    assert snapshot.available is True
    assert snapshot.power_source == "battery"
    assert snapshot.on_battery is True
    assert snapshot.battery_percent == 82


def test_macos_sleep_preventer_uses_system_sleep_assertion(monkeypatch):
    calls = []

    class FakeProcess:
        def poll(self):
            return None

        def terminate(self):
            calls.append("terminate")

        def wait(self, timeout=None):
            calls.append(("wait", timeout))

    def fake_popen(command, **kwargs):
        calls.append(command)
        return FakeProcess()

    monkeypatch.setattr(power.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(power.shutil, "which", lambda name: "/usr/bin/caffeinate" if name == "caffeinate" else None)
    monkeypatch.setattr(power.subprocess, "Popen", fake_popen)

    preventer = SleepPreventer()
    status = preventer.start()

    assert status["sleep_prevention_active"] is True
    assert calls[0] == ["/usr/bin/caffeinate", "-i", "-m", "-s"]
    assert "lid on battery" in status["sleep_prevention_message"]

    preventer.stop()

    assert "terminate" in calls


def test_linux_sleep_preventer_uses_systemd_inhibit(monkeypatch):
    calls = []

    class FakeProcess:
        def poll(self):
            return None

        def terminate(self):
            calls.append("terminate")

        def wait(self, timeout=None):
            calls.append(("wait", timeout))

    def fake_popen(command, **kwargs):
        calls.append(command)
        return FakeProcess()

    monkeypatch.setattr(power.platform, "system", lambda: "Linux")
    monkeypatch.setattr(power.shutil, "which", lambda name: "/usr/bin/systemd-inhibit" if name == "systemd-inhibit" else None)
    monkeypatch.setattr(power.subprocess, "Popen", fake_popen)

    preventer = SleepPreventer()
    status = preventer.start()

    assert status["sleep_prevention_active"] is True
    assert status["sleep_prevention_mode"] == "linux_systemd_inhibit"
    assert calls[0][0] == "/usr/bin/systemd-inhibit"

    preventer.stop()

    assert "terminate" in calls


def test_sleep_preventer_reports_unavailable_without_backend(monkeypatch):
    monkeypatch.setattr(power.platform, "system", lambda: "Linux")
    monkeypatch.setattr(power.shutil, "which", lambda name: None)

    status = SleepPreventer().start()

    assert status["sleep_prevention_active"] is False
    assert status["sleep_prevention_mode"] == "unavailable"
    assert "not available" in status["sleep_prevention_message"].lower()


def test_windows_sleep_preventer_uses_execution_state(monkeypatch):
    calls = []

    class Kernel32:
        def SetThreadExecutionState(self, flags):
            calls.append(flags)
            return 1

    class Windll:
        kernel32 = Kernel32()

    monkeypatch.setattr(power.platform, "system", lambda: "Windows")
    monkeypatch.setattr(power.ctypes, "windll", Windll(), raising=False)

    preventer = SleepPreventer()
    status = preventer.start()

    assert status["sleep_prevention_active"] is True
    assert status["sleep_prevention_mode"] == "windows_execution_state"

    stopped = preventer.stop()

    assert stopped["sleep_prevention_active"] is False
    assert calls == [0x80000001, 0x80000000]


def test_macos_closed_lid_upgrades_recording_and_releases_once(monkeypatch):
    events = []

    class Lease:
        active = True

    class Process:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout):
            pass

    def acquire():
        events.append("acquire")
        return Lease()

    monkeypatch.setattr(power.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(power.shutil, "which", lambda name: "/usr/bin/caffeinate")
    monkeypatch.setattr(power.subprocess, "Popen", lambda *a, **kw: Process())
    monkeypatch.setattr(power.closed_lid, "acquire", acquire)
    monkeypatch.setattr(power.closed_lid, "release", lambda lease: events.append("release") or True)
    preventer = SleepPreventer()
    assert not preventer.start()["closed_lid_active"]
    assert preventer.start(allow_closed_lid=True)["closed_lid_active"]
    assert preventer.start(allow_closed_lid=True)["closed_lid_active"]
    assert not preventer.stop()["closed_lid_active"]
    preventer.stop()
    assert events == ["acquire", "release"]


def test_macos_declined_permission_does_not_claim_closed_lid_support(monkeypatch):
    def denied():
        raise RuntimeError("Administrator access was declined")

    monkeypatch.setattr(power.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(power.shutil, "which", lambda name: None)
    monkeypatch.setattr(power.closed_lid, "acquire", denied)
    status = SleepPreventer().start(allow_closed_lid=True)
    assert not status["closed_lid_active"]
    assert "declined" in status["closed_lid_message"]
    assert "Keep the lid open" in status["closed_lid_message"]


def test_linux_closed_lid_upgrades_existing_inhibitor(monkeypatch):
    commands = []
    stopped = []

    class Process:
        def poll(self):
            return None

        def terminate(self):
            stopped.append(True)

        def wait(self, timeout):
            pass

    def popen(command, **kwargs):
        commands.append(command)
        return Process()

    monkeypatch.setattr(power.platform, "system", lambda: "Linux")
    monkeypatch.setattr(power.shutil, "which", lambda name: "/usr/bin/systemd-inhibit")
    monkeypatch.setattr(power.subprocess, "Popen", popen)
    preventer = SleepPreventer()
    preventer.start()
    status = preventer.start(allow_closed_lid=True)
    assert stopped == [True]
    assert "--what=idle:sleep" in commands[0]
    assert "--what=idle:sleep:handle-lid-switch" in commands[1]
    assert status["closed_lid_active"]
    preventer.stop()


def test_failed_sleep_restoration_is_reported(monkeypatch):
    preventer = SleepPreventer()
    preventer._lid_lease = object()
    monkeypatch.setattr(power.closed_lid, "release", lambda lease: False)
    status = preventer.stop()
    assert status["sleep_prevention_mode"] == "error"
    assert "sudo pmset disablesleep 0" in status["sleep_prevention_message"]
