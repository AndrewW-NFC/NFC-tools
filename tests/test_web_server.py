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


def test_session_start_stops_preview_meter_before_recording(monkeypatch):
    calls = []

    async def fake_stop():
        calls.append("preview_stopped")

    class FakeSession:
        def __init__(self, cfg, on_status=None):
            self.status = {"state": "idle"}

        async def start(self, force=False):
            calls.append(f"start:{force}")
            self.status = {"state": "recording"}

    monkeypatch.setattr(routes, "stop_sounddevice_preview_meter", fake_stop)
    monkeypatch.setattr(routes, "Session", FakeSession)
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes.state, "cfg", Config())

    response = TestClient(create_app()).post("/session/start")

    assert response.status_code == 200
    assert response.json()["state"] == "recording"
    assert calls == ["preview_stopped", "start:False"]


def test_session_analyze_pending_forces_analysis(monkeypatch):
    calls = []

    class FakeSession:
        status = {"state": "idle", "analysis": {"queue": ["sample.wav"], "active": False}}

        def start_pending_analysis(self, *, force=False):
            calls.append(force)
            self.status = {"state": "idle", "analysis": {"queue": [], "active": True}}
            return True

    monkeypatch.setattr(routes.state, "session", FakeSession())

    response = TestClient(create_app()).post("/session/analyze-pending", data={"force": "true"})

    assert response.status_code == 200
    assert calls == [True]


def test_checklist_page_shows_recording_checklist(monkeypatch):
    cfg = Config()
    cfg.recording.device = "test"
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes, "list_input_devices", lambda: [{"id": "test", "name": "Test mic", "ffmpeg_input": ["dummy"]}])
    monkeypatch.setattr(routes.installer, "status", lambda: {"birdnet": {"installed": True}, "nighthawk": {"installed": True}})
    monkeypatch.setattr(routes, "_disk_free_for_output", lambda: 20 * 1024 * 1024 * 1024)

    response = TestClient(create_app()).get("/checklist")

    assert response.status_code == 200
    assert "Recording Checklist" in response.text
    assert "My recording device is plugged in" in response.text
    assert "Tip: If you choose to run from battery power, turn off your display or lower its brightness." in response.text
    assert response.text.index("My recording device is plugged in") < response.text.index("I have selected my preferred microphone")
    assert "I have selected my preferred microphone" in response.text
    assert "Microphone currently selected is Test mic." in response.text
    assert "The sound meter is responsive" in response.text
    assert "Checking or not checking these boxes does not change how the recorder runs." in response.text
    assert "Recordings for the scheduled evening will be saved" not in response.text
    assert 'type="checkbox" autocomplete="off" checked' not in response.text
    assert 'type="checkbox" autocomplete="off"' in response.text


def test_checklist_state_is_not_restored_from_local_storage():
    script = (routes.Path(__file__).parents[1] / "src/nfc_tools/web/static/app.js").read_text()

    assert "nfcToolsRecordingChecklist" in script
    assert "localStorage.getItem" not in script
    assert "box.checked = false" in script


def test_existing_session_nfc_window_uses_session_date(monkeypatch):
    cfg = Config()
    cfg.site.latitude = 42.415
    cfg.site.longitude = -71.156
    cfg.site.timezone = "America/New_York"

    class FakeSession:
        status = {
            "state": "awaiting_start",
            "session_date": "2026-06-16",
            "scheduled_starts_at": "2026-06-16T20:50:00-04:00",
            "scheduled_ends_at": "2026-06-17T04:37:00-04:00",
            "ends_at": "2026-06-17T04:37:00-04:00",
        }

    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.state, "session", FakeSession())

    payload = TestClient(create_app()).get("/session/status").json()

    assert payload["nfc_starts_at"].startswith("2026-06-16")
    assert payload["nfc_ends_at"].startswith("2026-06-17")


def test_dashboard_and_settings_do_not_embed_recording_checklist(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes.doctor, "run_all", lambda: [])
    client = TestClient(create_app())

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "<h1>Tonight</h1>" not in response.text
    assert "<h1>Recording Checklist</h1>" not in response.text
    assert 'class="recording-checklist"' not in response.text

    settings = client.get("/settings")
    assert settings.status_code == 200
    assert "<h1>Recording Checklist</h1>" not in settings.text
    assert 'aria-hidden="true">%</span>' in settings.text


def test_dashboard_shows_recording_and_nfc_windows(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes.doctor, "run_all", lambda: [])

    response = TestClient(create_app()).get("/dashboard")

    assert response.status_code == 200
    assert "Recording window:" in response.text
    assert response.text.count("<summary>Explain</summary>") == 2
    assert "The full recording time." in response.text
    assert "starts a new audio file at the beginning and end" in response.text
    assert "strict NFC protocol window" in response.text
    assert "after the NFC period" in response.text
    assert "Incidental" in response.text
    assert "NFC counting window:" in response.text
    assert "astronomical dusk to astronomical dawn" in response.text
    assert "observations you can submit to eBird" in response.text
    assert "Download log (CSV)" not in response.text
    assert "Download log" in response.text
    assert "nfc-start" in response.text
    assert "nfc-end" in response.text


def test_settings_page_renders_schedule_controls_without_removed_status(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes, "list_input_devices", lambda: [])
    monkeypatch.setattr(routes.installer, "status", lambda: {"birdnet": {"installed": True}, "nighthawk": {"installed": True}})

    response = TestClient(create_app()).get("/settings")

    assert response.status_code == 200
    assert 'name="start_time"' in response.text
    assert 'name="end_time"' in response.text
    assert 'name="segment_minutes"' in response.text
    assert "BirdNET's minimum confidence. Lower values mean rarer results but also more incorrect results." in response.text
    assert "Currently enabled:" not in response.text
    assert "<h2>Status</h2>" not in response.text


def test_detection_review_routes_are_not_registered():
    client = TestClient(create_app())

    assert client.get("/detections").status_code == 404
    assert client.get("/clip-file").status_code == 404
    assert client.get("/export/2026-06-16.csv").status_code == 404


def test_settings_save_persists_power_preferences(monkeypatch):
    saved = []
    cfg = Config()
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.config_mod, "save", lambda value: saved.append(value))

    response = TestClient(create_app()).post(
        "/settings/save",
        data={
            "site_name": cfg.site.name,
            "latitude": str(cfg.site.latitude),
            "longitude": str(cfg.site.longitude),
            "device_id": "test",
            "recording_backend": "auto",
            "format_preset": cfg.recording.format_preset,
            "start_time": cfg.schedule.start_time,
            "end_time": cfg.schedule.end_time,
            "segment_minutes": str(cfg.schedule.segment_minutes),
            "birdnet_min_conf": str(cfg.analyzers.birdnet_min_conf),
            "sleep_prevention": "recording_only",
            "analysis_policy": "defer_below_threshold",
            "min_battery_percent_for_analysis": "45",
            "low_battery_warning_percent": "15",
            "critical_battery_percent": "8",
            "critical_battery_action": "defer_analysis",
            "enabled_analyzers": ["birdnet"],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert saved
    assert cfg.power.sleep_prevention == "recording_only"
    assert cfg.power.analysis_policy == "defer_below_threshold"
    assert cfg.power.min_battery_percent_for_analysis == 45
    assert cfg.power.low_battery_warning_percent == 15
    assert cfg.power.critical_battery_percent == 8
    assert cfg.power.critical_battery_action == "defer_analysis"


def test_settings_coordinate_update_keeps_existing_timezone_when_new_value_is_invalid(monkeypatch):
    cfg = Config()
    cfg.site.timezone = "America/New_York"
    saved = []
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.config_mod, "save", lambda value: saved.append(value))

    response = TestClient(create_app()).post(
        "/settings/site-coordinates",
        data={"latitude": "42.4", "longitude": "-71.1", "timezone": "Invalid/Timezone"},
    )

    assert response.status_code == 200
    assert cfg.site.timezone == "America/New_York"
    assert saved


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
