from fastapi.testclient import TestClient

import nfc_tools.web.routes as routes
from nfc_tools.config import Config
from nfc_tools.web.server import create_app
from nfc_tools.web.server import browser_url


def test_browser_url_uses_loopback_for_wildcard_hosts():
    assert browser_url("0.0.0.0", 8765) == "http://127.0.0.1:8765/"
    assert browser_url("::", 8765) == "http://127.0.0.1:8765/"


def test_browser_url_preserves_specific_host():
    assert browser_url("127.0.0.1", 8765) == "http://127.0.0.1:8765/"


def test_mic_level_pause_stops_preview_meter(monkeypatch):
    calls = []

    async def fake_stop():
        calls.append("stopped")

    monkeypatch.setattr(routes, "stop_sounddevice_preview_meter", fake_stop)

    response = TestClient(create_app()).post("/api/mic-level/pause")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == ["stopped"]


def test_ffmpeg_standby_preview_requires_on_demand(monkeypatch):
    cfg = Config()
    cfg.recording.device = "test"
    cfg.recording.backend = "ffmpeg"
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes, "list_input_devices", lambda: [{"id": "test", "name": "Test mic", "ffmpeg_input": ["dummy"]}])
    monkeypatch.setattr(routes.platform, "system", lambda: "Linux")

    def fail_measure(*args, **kwargs):
        raise AssertionError("ffmpeg preview should not run automatically")

    monkeypatch.setattr(routes, "measure_levels", fail_measure)

    response = TestClient(create_app()).get("/api/mic-level")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_on_demand"] is True
    assert payload["paused"] is True


def test_ffmpeg_preview_runs_when_requested_on_demand(monkeypatch):
    cfg = Config()
    cfg.recording.device = "test"
    cfg.recording.backend = "ffmpeg"
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes, "list_input_devices", lambda: [{"id": "test", "name": "Test mic", "ffmpeg_input": ["dummy"]}])
    monkeypatch.setattr(routes.platform, "system", lambda: "Linux")

    async def fake_measure(*args, **kwargs):
        return {"mean_db": -35.0, "peak_db": -12.0}

    monkeypatch.setattr(routes, "measure_levels", fake_measure)

    response = TestClient(create_app()).get("/api/mic-level?on_demand=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requires_on_demand"] is True
    assert payload["rms_db"] == -35.0
    assert payload["peak_db"] == -12.0
