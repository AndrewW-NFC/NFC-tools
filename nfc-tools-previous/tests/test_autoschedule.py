from types import SimpleNamespace

from nfc_tools import autoschedule


def test_linux_autoschedule_writes_systemd_user_units(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(stdout="active", stderr="", returncode=0)

    monkeypatch.setattr(autoschedule.platform, "system", lambda: "Linux")
    monkeypatch.setattr(autoschedule, "_systemd_user_dir", lambda: tmp_path)
    monkeypatch.setattr(autoschedule, "_start_command", lambda: ["/usr/bin/nfc", "record-once"])
    monkeypatch.setattr(autoschedule.subprocess, "run", fake_run)

    status = autoschedule.install("20:50")

    assert status.enabled is True
    assert status.backend == "systemd"
    assert "ExecStart=/usr/bin/nfc record-once" in (tmp_path / "org.nfctools.recorder.service").read_text()
    assert "OnCalendar=*-*-* 20:50:00" in (tmp_path / "org.nfctools.recorder.timer").read_text()
    assert any("enable" in cmd for cmd, _ in calls)


def test_linux_autoschedule_quotes_paths_with_spaces(tmp_path, monkeypatch):
    monkeypatch.setattr(autoschedule.platform, "system", lambda: "Linux")
    monkeypatch.setattr(autoschedule, "_systemd_user_dir", lambda: tmp_path)
    monkeypatch.setattr(
        autoschedule,
        "_start_command",
        lambda: ["/home/user/NFC Tools/.venv/bin/python", "-m", "nfc_tools", "record-once"],
    )
    monkeypatch.setattr(
        autoschedule.subprocess,
        "run",
        lambda cmd, **kwargs: SimpleNamespace(stdout="active", stderr="", returncode=0),
    )

    autoschedule.install("20:50")

    service = (tmp_path / "org.nfctools.recorder.service").read_text()
    assert "ExecStart='/home/user/NFC Tools/.venv/bin/python' -m nfc_tools record-once" in service


def test_windows_autoschedule_creates_daily_task(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    monkeypatch.setattr(autoschedule.platform, "system", lambda: "Windows")
    monkeypatch.setattr(autoschedule, "_start_command", lambda: ["nfc", "record-once"])
    monkeypatch.setattr(autoschedule.subprocess, "run", fake_run)

    status = autoschedule.install("20:50")

    assert status.enabled is True
    assert status.backend == "schtasks"
    cmd = calls[0][0]
    assert cmd[:5] == ["schtasks", "/Create", "/F", "/SC", "DAILY"]
    assert cmd[cmd.index("/ST") + 1] == "20:50"
    assert cmd[cmd.index("/TR") + 1] == '"nfc" "record-once"'
