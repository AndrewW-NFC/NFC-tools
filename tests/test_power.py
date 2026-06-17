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
