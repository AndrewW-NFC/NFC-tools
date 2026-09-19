from types import SimpleNamespace

from fastapi.testclient import TestClient

import nfc_tools.web.routes as routes
import nfc_tools.web.routes_import as import_routes
import nfc_tools.web.routes_readiness as readiness_routes
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


def test_checklist_page_is_removed():
    response = TestClient(create_app()).get("/checklist")

    assert response.status_code == 404


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
    assert payload["civil_starts_at"].startswith("2026-06-16")
    assert payload["civil_ends_at"].startswith("2026-06-17")


def test_dashboard_and_settings_do_not_embed_recording_checklist(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes.doctor, "run_all", lambda: [])
    client = TestClient(create_app())

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "<h1>Tonight</h1>" not in response.text
    assert "Recording Checklist" not in response.text
    assert 'class="recording-checklist"' not in response.text

    settings = client.get("/settings")
    assert settings.status_code == 200
    assert "Recording Checklist" not in settings.text
    assert 'aria-hidden="true">%</span>' in settings.text


def test_first_launch_goes_to_dashboard(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes.doctor, "run_all", lambda: [])

    response = TestClient(create_app()).get("/")

    assert response.status_code == 200
    assert "Recording window:" in response.text


def test_wizard_routes_are_removed():
    response = TestClient(create_app()).get("/wizard")

    assert response.status_code == 404


def test_diagnostics_page_is_registered_after_route_split(monkeypatch):
    monkeypatch.setattr("nfc_tools.web.routes_diagnostics.doctor.run_all", lambda: [])

    response = TestClient(create_app()).get("/diagnostics")

    assert response.status_code == 200
    assert "Recording path diagnostics" in response.text
    assert "/static/diagnostics_page.js" in response.text


def test_readiness_page_shows_grouped_idle_checks(monkeypatch):
    monkeypatch.setattr(readiness_routes.state, "cfg", Config())
    monkeypatch.setattr(readiness_routes.state, "config_revision", 7)

    response = TestClient(create_app()).get("/readiness")

    assert response.status_code == 200
    assert "Readiness Check" in response.text
    assert 'data-config-revision="7"' in response.text
    assert "Run readiness check" in response.text
    assert "Recording Input" in response.text
    assert "Storage" in response.text
    assert "Overnight Reliability" in response.text
    assert "Supporting Services" in response.text
    assert "Configured microphone is available and can be opened." in response.text
    assert "Environment logging is working." in response.text
    assert response.text.count("Not checked") == 10
    assert "/static/readiness_page.js" in response.text


def test_readiness_run_endpoint_returns_grouped_results(monkeypatch):
    cfg = Config()
    monkeypatch.setattr(readiness_routes.state, "cfg", cfg)
    monkeypatch.setattr(readiness_routes.state, "session", None)
    monkeypatch.setattr(readiness_routes.state, "config_revision", 3)

    async def fake_run(config, active_session_status=None):
        assert config is cfg
        assert active_session_status is None
        return [
            {
                "id": "recording_input",
                "title": "Recording Input",
                "checks": [
                    {
                        "id": "microphone_open",
                        "label": "Configured microphone is available and can be opened.",
                        "status": "ready",
                        "detail": "Opened Test mic.",
                    },
                ],
            },
        ]

    monkeypatch.setattr(readiness_routes, "run_readiness_checks", fake_run)

    response = TestClient(create_app()).post("/readiness/run")

    assert response.status_code == 200
    payload = response.json()
    assert payload["config_revision"] == 3
    assert payload["groups"][0]["checks"][0]["status"] == "ready"


def test_readiness_status_labels_use_agreed_wording():
    script = (routes.Path(__file__).parents[1] / "src/nfc_tools/web/static/readiness_page.js").read_text(
        encoding="utf-8"
    )

    assert "✅ Ready" in script
    assert "⚠️ Note" in script
    assert "❌ Problem" in script
    assert "Needs attention" not in script
    assert "⚠️ Warning" not in script


def test_dashboard_shows_recording_and_nfc_windows(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes.state, "session", None)
    monkeypatch.setattr(routes.doctor, "run_all", lambda: [])

    response = TestClient(create_app()).get("/dashboard")

    assert response.status_code == 200
    assert "Recording window:" in response.text
    assert response.text.count("<summary>Explain</summary>") == 2
    assert "The full recording time." in response.text
    assert "strict astronomical twilight preset" in response.text
    assert "astronomical dusk to astronomical dawn" in response.text
    assert "civil-dusk-to-civil-dawn window" in response.text
    assert "NFC counting window:" in response.text
    assert "astronomical dusk to astronomical dawn" in response.text
    assert "separate eBird checklists" in response.text
    assert "Download log (CSV)" not in response.text
    assert "Download log" in response.text
    assert "nfc-start" in response.text
    assert "nfc-end" in response.text


def test_settings_page_renders_schedule_controls_without_removed_status(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes, "list_input_devices", lambda: [])
    monkeypatch.setattr(
        routes.installer,
        "status",
        lambda: {
            "ffmpeg": {"installed": False, "path": None},
            "birdnet": {"installed": True},
            "nighthawk": {"installed": True},
        },
    )

    response = TestClient(create_app()).get("/settings")

    assert response.status_code == 200
    assert 'id="default-location-settings"' in response.text
    assert "Default location" in response.text
    assert "Your recording name and coordinates are used for recording windows, analyzers, and weather. eBird is optional and configured separately below." in response.text
    assert 'name="start_time"' in response.text
    assert 'name="end_time"' in response.text
    assert 'name="segment_minutes"' in response.text
    assert 'name="save_location"' in response.text
    assert 'id="choose-save-location"' in response.text
    assert 'id="use-desktop-save-location"' in response.text
    assert 'name="schedule_mode"' in response.text
    assert "Follow local twilight automatically" in response.text
    assert "Use fixed clock times" in response.text
    assert "Astronomical twilight (strict NFC protocol)" in response.text
    assert "Civil twilight (loose NFC protocol)" in response.text
    assert response.text.index("Civil twilight (loose NFC protocol)") < response.text.index(
        "Astronomical twilight (strict NFC protocol)"
    )
    assert "Enter a folder path" not in response.text
    assert "BirdNET's minimum confidence. Lower values mean rarer results but also more incorrect results." in response.text
    assert 'name="ebird_state_province"' in response.text
    assert 'name="ebird_hotspot_id"' in response.text
    assert "Recording engine" in response.text
    assert "Not installed yet" in response.text
    assert response.text.count("Installed") >= 2
    assert "Currently enabled:" not in response.text
    assert "<h2>Status</h2>" not in response.text


def test_import_recordings_page_is_registered(monkeypatch):
    cfg = Config()
    cfg.site.name = "Test Ridge"
    cfg.site.ebird_hotspot_id = "L5129545"
    monkeypatch.setattr(import_routes.state, "cfg", cfg)

    response = TestClient(create_app()).get("/import-recordings")

    assert response.status_code == 200
    assert "Import Recordings" in response.text
    assert 'id="start-import-run"' in response.text
    assert 'id="resume-import-run"' in response.text
    assert "Import existing recordings, analyze them, and create review clips plus eBird CSVs" in response.text
    assert 'id="import-next-action"' in response.text
    assert "Next: choose analyzers." in response.text
    assert 'id="choose-import-source-folder"' in response.text
    assert 'id="choose-import-output-folder"' in response.text
    assert 'id="scan-import-recordings"' in response.text
    assert 'id="scan-and-build-import-review"' not in response.text
    assert 'id="scan-import-folders"' not in response.text
    assert 'id="build-import-timeline"' not in response.text
    assert 'id="import-start-date"' not in response.text
    assert 'id="import-start-time"' not in response.text
    assert "No source folder selected" in response.text
    assert "No output folder selected" in response.text
    assert "Enter a folder path" not in response.text
    assert "Source formats NFC Tools can find for import: AIFF, FLAC, M4A, MP3, OGG, WAV" in response.text
    assert "AIF, AIFF" not in response.text
    assert "WAV, WAVE" not in response.text
    assert 'class="stage-body"' in response.text
    assert 'id="import-location-map"' in response.text
    assert 'id="import-current-location"' in response.text
    assert 'id="import-latitude"' in response.text
    assert 'id="import-longitude"' in response.text
    assert 'id="import-ebird-state-province"' in response.text
    assert "eBird exports (optional)" in response.text
    assert "No location code needed" in response.text
    assert 'id="import-ebird-export-enabled"' in response.text
    assert 'id="import-timezone-label"' in response.text
    assert 'id="timeline-suggestion-summary"' in response.text
    assert 'id="timeline-responsibility-check"' in response.text
    assert "Scan recordings to build the timeline review." in response.text
    assert 'id="import-output-summary"' in response.text
    assert "/static/import_page.js" in response.text
    assert 'id="import-setup-fields" disabled' not in response.text
    assert 'id="import-run-log"' not in response.text
    assert "Follow latest activity" not in response.text
    assert 'id="import-birdnet-year-round"' in response.text
    assert '24-hour' in response.text
    assert 'Time and location are the integrity layer' not in response.text
    assert 'Time is treated as sacred' not in response.text
    assert 'Import processing writes 48 kHz' not in response.text
    assert 'You can leave this page while the app remains open' not in response.text


def test_import_recordings_navigation_link_is_active(monkeypatch):
    monkeypatch.setattr(import_routes.state, "cfg", Config())

    response = TestClient(create_app()).get("/import-recordings")

    assert response.status_code == 200
    assert '<a href="/import-recordings" class="active">Import Recordings</a>' in response.text


def test_import_recordings_source_folder_picker_returns_selected_folder(monkeypatch):
    calls = []

    def fake_choose_directory(current_path, *, title):
        calls.append((current_path, title))
        return "/Volumes/Recorder Archive"

    monkeypatch.setattr(import_routes, "choose_directory", fake_choose_directory)

    response = TestClient(create_app()).post(
        "/import-recordings/choose-source-folder",
        data={"current_source_folder": "/Volumes/Old"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "path": "/Volumes/Recorder Archive",
        "display": import_routes._display_path(import_routes.Path("/Volumes/Recorder Archive")),
    }
    assert calls == [("/Volumes/Old", "Choose folder with recordings to process")]


def test_import_recordings_output_folder_picker_returns_selected_folder(monkeypatch):
    calls = []

    def fake_choose_directory(current_path, *, title):
        calls.append((current_path, title))
        return "/Volumes/NFC Processed"

    monkeypatch.setattr(import_routes, "choose_directory", fake_choose_directory)

    response = TestClient(create_app()).post(
        "/import-recordings/choose-output-folder",
        data={"current_output_folder": "/Volumes/Old Output"},
    )

    assert response.status_code == 200
    assert response.json()["path"] == "/Volumes/NFC Processed"
    assert calls == [("/Volumes/Old Output", "Choose where NFC Tools writes processed recordings")]


def test_import_recordings_folder_picker_reports_cancel(monkeypatch):
    monkeypatch.setattr(import_routes, "choose_directory", lambda current_path, *, title: None)

    response = TestClient(create_app()).post("/import-recordings/choose-source-folder")

    assert response.status_code == 200
    assert response.json() == {"ok": False, "cancelled": True}


def test_import_recordings_scan_reports_audio_and_capacity(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    audio = source / "recorder_2026-09-14_18-00-00.wav"
    audio.write_bytes(b"0" * 2048)
    (source / "notes.txt").write_text("not audio", encoding="utf-8")

    response = TestClient(create_app()).post(
        "/import-recordings/scan",
        data={"source_folder": str(source), "output_folder": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["source"]["audio_count"] == 1
    assert payload["source"]["source_bytes"] == 2048
    assert payload["source"]["extension_counts"] == {"WAV": 1}
    assert payload["source"]["review_file_count"] == 1
    assert payload["source"]["review_hidden_count"] == 0
    assert payload["source"]["review_file_limit"] is None
    assert payload["source"]["samples"][0]["relative_path"] == "recorder_2026-09-14_18-00-00.wav"
    assert payload["source"]["samples"][0]["detected_start"] == "2026-09-14 18:00:00"
    assert payload["output"]["free_bytes"] > 0
    assert payload["estimate"]["processed_audio"]["high_bytes"] == 2048
    assert payload["source"]["unknown_duration_count"] == 1


def test_import_recordings_scan_uses_ffmpeg_duration_metadata_for_non_wav(tmp_path, monkeypatch):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    audio = source / "recorder_2026-09-14_18-00-00.mp3"
    audio.write_bytes(b"fake mp3 bytes")
    monkeypatch.setattr(import_routes, "find_ffmpeg", lambda: "/usr/bin/ffmpeg")
    monkeypatch.setattr(
        import_routes.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="",
            stderr="Duration: 00:02:03.45, start: 0.000000, bitrate: 192 kb/s",
        ),
    )

    response = TestClient(create_app()).post(
        "/import-recordings/scan",
        data={"source_folder": str(source), "output_folder": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    review_file = payload["source"]["review_files"][0]
    assert review_file["relative_path"] == "recorder_2026-09-14_18-00-00.mp3"
    assert review_file["duration_seconds"] == 123.45
    assert review_file["duration_display"] == "2:03"


def test_import_recordings_scan_includes_every_file_for_bulk_correction(tmp_path, monkeypatch):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for index in range(203):
        (source / f"recorder_2026-09-14_18-{index:02d}-00.wav").write_bytes(b"0" * 128)
    monkeypatch.setattr(import_routes, "_duration_seconds", lambda path, ffmpeg_path=None: 60.0)

    response = TestClient(create_app()).post(
        "/import-recordings/scan",
        data={"source_folder": str(source), "output_folder": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["audio_count"] == 203
    assert payload["source"]["review_file_count"] == 203
    assert payload["source"]["review_hidden_count"] == 0
    assert len(payload["source"]["review_files"]) == 203


def test_import_recordings_scan_groups_equivalent_extensions(tmp_path):
    source = tmp_path / "source"
    output = tmp_path / "output"
    source.mkdir()
    output.mkdir()
    for filename in ("one.aif", "two.aiff", "three.wav", "four.wave"):
        (source / filename).write_bytes(b"0" * 128)

    response = TestClient(create_app()).post(
        "/import-recordings/scan",
        data={"source_folder": str(source), "output_folder": str(output)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"]["audio_count"] == 4
    assert payload["source"]["extension_counts"] == {"AIFF": 2, "WAV": 2}


def test_import_recordings_scan_allows_nested_output_without_warning(tmp_path):
    source = tmp_path / "source"
    output = source / "processed"
    output.mkdir(parents=True)
    (source / "2026-09-14_18-00-00.wav").write_bytes(b"0" * 128)

    response = TestClient(create_app()).post(
        "/import-recordings/scan",
        data={"source_folder": str(source), "output_folder": str(output)},
    )

    assert response.status_code == 200
    assert not any("inside the source folder" in warning for warning in response.json()["warnings"])


def test_import_recordings_site_timezone_does_not_save_settings(monkeypatch):
    cfg = Config()
    cfg.site.timezone = "America/Chicago"
    monkeypatch.setattr(import_routes.state, "cfg", cfg)
    monkeypatch.setattr(
        import_routes,
        "timezone_for_coordinates",
        lambda latitude, longitude: "America/Los_Angeles",
    )
    saved = []
    monkeypatch.setattr(import_routes.config_mod, "save", lambda cfg: saved.append(cfg))

    response = TestClient(create_app()).post(
        "/import-recordings/site-timezone",
        data={"latitude": "34.05", "longitude": "-118.25", "fallback": "America/New_York"},
    )

    assert response.status_code == 200
    assert response.json()["timezone"] == "America/Los_Angeles"
    assert cfg.site.timezone == "America/Chicago"
    assert saved == []


def test_import_run_status_ignores_completed_runner_without_saved_job(monkeypatch):
    class CompleteRunner:
        job = {"state": "complete"}

        def status(self):
            raise AssertionError("A completed unsaved runner should not lock a fresh import page.")

    monkeypatch.setattr(import_routes.manager, "runner", CompleteRunner())

    response = TestClient(create_app()).get("/import-recordings/run")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "job": None}


def test_install_status_reports_current_components(monkeypatch):
    monkeypatch.setattr(
        routes.installer,
        "status",
        lambda: {
            "ffmpeg": {"installed": True, "path": "/usr/bin/ffmpeg"},
            "birdnet": {"installed": False, "python": None},
            "nighthawk": {"installed": True, "python": "/tmp/nighthawk/bin/python"},
        },
    )

    response = TestClient(create_app()).get("/install/status")

    assert response.status_code == 200
    assert response.json()["ffmpeg"]["installed"] is True
    assert response.json()["birdnet"]["installed"] is False


def test_choose_save_location_returns_selected_folder(monkeypatch):
    cfg = Config()
    cfg.recording.save_location = "/Volumes/Old"
    monkeypatch.setattr(routes.state, "cfg", cfg)

    calls = []

    def fake_choose_directory(current_path, *, title):
        calls.append((current_path, title))
        return "/Volumes/NFC Drive"

    monkeypatch.setattr(routes, "choose_directory", fake_choose_directory)

    response = TestClient(create_app()).post(
        "/settings/choose-save-location",
        data={"current_save_location": "/Volumes/Current"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "path": "/Volumes/NFC Drive",
        "display": routes._display_path(routes.Path("/Volumes/NFC Drive")),
    }
    assert calls == [("/Volumes/Current", "Choose where NFC Tools saves recordings")]


def test_choose_save_location_reports_cancel(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())
    monkeypatch.setattr(routes, "choose_directory", lambda current_path, *, title: None)

    response = TestClient(create_app()).post("/settings/choose-save-location")

    assert response.status_code == 200
    assert response.json() == {"ok": False, "cancelled": True}


def test_choose_save_location_reports_unavailable(monkeypatch):
    monkeypatch.setattr(routes.state, "cfg", Config())

    def fake_choose_directory(current_path, *, title):
        raise routes.FolderPickerUnavailable("Folder chooser unavailable")

    monkeypatch.setattr(routes, "choose_directory", fake_choose_directory)

    response = TestClient(create_app()).post("/settings/choose-save-location")

    assert response.status_code == 503
    assert response.json() == {"ok": False, "error": "Folder chooser unavailable"}


def test_settings_save_persists_automatic_twilight_schedule(monkeypatch):
    saved = []
    cfg = Config()
    cfg.schedule.mode = "manual"
    cfg.schedule.auto_apply_preset = False
    cfg.schedule.preset = None
    cfg.schedule.start_time = "20:50"
    cfg.schedule.end_time = "04:37"
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.config_mod, "save", lambda value: saved.append(value))
    monkeypatch.setattr(routes, "timezone_for_coordinates", lambda lat, lon: "America/New_York")
    monkeypatch.setattr(
        routes,
        "current_schedule_preview",
        lambda value: SimpleNamespace(start_time="20:59", end_time="04:32"),
    )

    response = TestClient(create_app()).post(
        "/settings/save",
        data={
            "site_name": cfg.site.name,
            "latitude": str(cfg.site.latitude),
            "longitude": str(cfg.site.longitude),
            "ebird_state_province": "us-ma",
            "ebird_hotspot_id": "https://ebird.org/hotspot/L5129545",
            "device_id": "test",
            "save_location": "",
            "recording_backend": "auto",
            "format_preset": cfg.recording.format_preset,
            "schedule_mode": "twilight",
            "schedule_preset": "astronomical",
            "start_time": "20:50",
            "end_time": "04:37",
            "segment_minutes": str(cfg.schedule.segment_minutes),
            "birdnet_min_conf": str(cfg.analyzers.birdnet_min_conf),
            "sleep_prevention": cfg.power.sleep_prevention,
            "analysis_policy": cfg.power.analysis_policy,
            "min_battery_percent_for_analysis": str(cfg.power.min_battery_percent_for_analysis),
            "low_battery_warning_percent": str(cfg.power.low_battery_warning_percent),
            "critical_battery_percent": str(cfg.power.critical_battery_percent),
            "critical_battery_action": cfg.power.critical_battery_action,
            "enabled_analyzers": ["birdnet"],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert saved
    assert cfg.schedule.mode == "twilight"
    assert cfg.schedule.auto_apply_preset is True
    assert cfg.schedule.preset == "astronomical"
    assert cfg.schedule.start_time == "20:59"
    assert cfg.schedule.end_time == "04:32"
    assert cfg.site.ebird_state_province == "MA"
    assert cfg.site.ebird_hotspot_id == "L5129545"


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
    monkeypatch.setattr(routes, "timezone_for_coordinates", lambda lat, lon: "America/New_York")

    response = TestClient(create_app()).post(
        "/settings/save",
        data={
            "site_name": cfg.site.name,
            "latitude": str(cfg.site.latitude),
            "longitude": str(cfg.site.longitude),
            "device_id": "test",
            "save_location": "/Volumes/NFC Drive",
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
    assert cfg.recording.save_location == "/Volumes/NFC Drive"


def test_settings_coordinate_update_sets_timezone_from_map_location(monkeypatch):
    cfg = Config()
    cfg.site.timezone = "Etc/UTC"
    saved = []
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.config_mod, "save", lambda value: saved.append(value))
    monkeypatch.setattr(routes, "timezone_for_coordinates", lambda lat, lon: "America/New_York")

    response = TestClient(create_app()).post(
        "/settings/site-coordinates",
        data={"latitude": "42.4", "longitude": "-71.1"},
    )

    assert response.status_code == 200
    assert cfg.site.timezone == "America/New_York"
    assert response.json()["timezone"] == "America/New_York"
    assert saved


def test_settings_coordinate_update_keeps_existing_timezone_when_lookup_fails(monkeypatch):
    cfg = Config()
    cfg.site.timezone = "America/New_York"
    saved = []
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes.config_mod, "save", lambda value: saved.append(value))
    monkeypatch.setattr(routes, "timezone_for_coordinates", lambda lat, lon: None)

    response = TestClient(create_app()).post(
        "/settings/site-coordinates",
        data={"latitude": "42.4", "longitude": "-71.1"},
    )

    assert response.status_code == 200
    assert cfg.site.timezone == "America/New_York"
    assert response.json()["timezone"] == "America/New_York"
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


def test_import_filename_inference_rejects_invalid_calendar_values():
    for name in ("2026-02-29_23-30-00.wav", "2026-08-08_25-00-00.wav", "2026-13-01_00-00.wav"):
        assert import_routes._detected_start_from_name(name) is None
    assert import_routes._detected_start_from_name("2024-02-29_23-30.wav") == "2024-02-29 23:30:00"
