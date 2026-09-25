import wave
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from nfc_tools import night_status, clip_exporter
from nfc_tools.config import Config
from nfc_tools.session import Session
from nfc_tools.session_logging import append_log_row
from nfc_tools.web.server import create_app
from nfc_tools.web import routes_nights


def recording(nd, name="001_NFC_2026-09-17_23-59-50.wav", seconds=20):
    path = nd / "audio" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x00\x01" * 8000 * seconds)
    return path


def config():
    cfg = Config()
    cfg.site.timezone = "UTC"
    cfg.analyzers.enabled = ["birdnet", "nighthawk"]
    return cfg


def test_coverage_merges_windows_and_overlap_and_reports_gaps(tmp_path):
    nd = tmp_path / "2026-09-17"
    recording(nd)
    recording(nd, "002_NFC_2026-09-18_00-00-00.wav")
    for event in ["session_scheduled", "recording_started"]:
        append_log_row(nd / "logs" / "session_log.csv", {
            "event": event, "details": {"scheduled_starts_at": "2026-09-17T23:59:40+00:00",
                                        "scheduled_ends_at": "2026-09-18T00:00:30+00:00"}})
    summary = night_status.summarize(nd, config())
    assert summary["expected_seconds"] == 50
    assert summary["recorded_seconds"] == 40
    assert summary["covered_seconds"] == 30
    assert summary["missing_seconds"] == 20
    assert len(summary["gaps"]) == 2
    assert summary["pending_files"] == 2


def test_unknown_window_and_truncated_recording_not_counted(tmp_path):
    wav = recording(tmp_path)
    wav.write_bytes(wav.read_bytes()[:-100])
    summary = night_status.summarize(tmp_path, config())
    assert summary["coverage"] == "unknown"
    assert summary["invalid_files"] == 1
    assert summary["recorded_seconds"] == 0
    assert summary["pending_files"] == 0


def test_recovery_skips_successful_analyzer_and_retries_failed_one(tmp_path, monkeypatch):
    wav = recording(tmp_path)
    runs, clips = [], []
    fail = {"nighthawk": True}
    class Plugin:
        def __init__(self, name): self.name = name
        def run(self, wav, out, cfg):
            runs.append(self.name)
            out.mkdir(parents=True, exist_ok=True)
            (out / "result.txt").write_text("result")
            return SimpleNamespace(success=not fail.get(self.name, False), output_dir=out, message="test")
    monkeypatch.setattr("nfc_tools.session.analyzers.get", Plugin)
    monkeypatch.setattr("nfc_tools.session.notify", lambda *args: None)
    monkeypatch.setattr(clip_exporter, "export_analyzer_clips", lambda wav, name, *args: clips.append(name) or 1)
    first = Session(config())
    first._analyze_one(wav)
    first._pool.shutdown()
    assert runs == ["birdnet", "nighthawk"]
    fail["nighthawk"] = False
    restarted = Session(config())
    restarted._analyze_one(wav, resume=True)
    restarted._analyze_one(wav, resume=True)
    restarted._pool.shutdown()
    assert runs == ["birdnet", "nighthawk", "nighthawk"]
    assert clips == ["birdnet", "nighthawk"]
    assert night_status.summarize(tmp_path, config())["pending_files"] == 0


def test_failed_clips_retry_without_rerunning_inference(tmp_path, monkeypatch):
    wav = recording(tmp_path)
    cfg = config()
    cfg.analyzers.enabled = ["birdnet"]
    runs = []
    def run(wav, out, cfg):
        runs.append(wav)
        return SimpleNamespace(success=True, output_dir=out, message="")
    monkeypatch.setattr("nfc_tools.session.analyzers.get", lambda name: SimpleNamespace(run=run))
    def fail(*args): raise RuntimeError("disk full")
    monkeypatch.setattr(clip_exporter, "export_analyzer_clips", fail)
    s = Session(cfg)
    s._analyze_one(wav)
    report = night_status.summarize(tmp_path, cfg)
    assert report["pending_files"] == 1
    assert report["files"][0]["analyzers"]["birdnet"]["error"] == "disk full"
    monkeypatch.setattr(clip_exporter, "export_analyzer_clips", lambda *args: 0)
    s._analyze_one(wav, resume=True)
    s._pool.shutdown()
    assert len(runs) == 1
    assert night_status.summarize(tmp_path, cfg)["pending_files"] == 0


def test_running_checkpoint_and_changed_audio_require_recovery(tmp_path):
    wav = recording(tmp_path)
    data = {"files": {}}
    entry = night_status.file_progress(tmp_path, wav, data)
    entry["analyzers"]["birdnet"] = {"analysis": "running", "clips": "pending"}
    night_status.save_progress(tmp_path, data)
    assert night_status.summarize(tmp_path, config())["pending_files"] == 1
    entry["analyzers"]["birdnet"] = {"analysis": "ok", "clips": "ok"}
    night_status.save_progress(tmp_path, data)
    recording(tmp_path, seconds=21)
    loaded = night_status.load_progress(tmp_path)
    assert night_status.file_progress(tmp_path, wav, loaded)["analyzers"] == {}


def test_corrupt_progress_is_not_silently_reset(tmp_path):
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "analysis_progress.json").write_text("{")
    with pytest.raises(ValueError):
        night_status.load_progress(tmp_path)


def test_night_routes_reject_active_recording_and_invalid_night(tmp_path, monkeypatch):
    cfg = config()
    cfg.recording.save_location = str(tmp_path)
    recording(tmp_path / "2026-09-17")
    monkeypatch.setattr(routes_nights.state, "cfg", cfg)
    monkeypatch.setattr(routes_nights.state, "session", SimpleNamespace(status={"state": "recording"}))
    client = TestClient(create_app())
    assert client.get('/nights').status_code == 200
    assert client.get('/api/nights/not-a-date').status_code == 400
    assert client.get('/api/nights/2026-09-17').json()["busy"] is True
    assert client.post('/api/nights/2026-09-17/recover').status_code == 409


def test_recovery_refreshes_exports_even_without_pending_analysis(tmp_path, monkeypatch):
    cfg = config()
    cfg.analyzers.enabled = []
    recording(tmp_path)
    calls = []
    monkeypatch.setattr(Session, '_refresh_ebird_exports', lambda self, path: calls.append(path))
    monkeypatch.setattr(Session, '_start_sleep_prevention', lambda *args: None)
    monkeypatch.setattr(Session, '_release_sleep_prevention', lambda *args: None)
    routes_nights.recover(tmp_path, cfg)
    assert calls == [tmp_path]
    assert not routes_nights.recovery_active()


def test_legacy_success_keeps_inference_but_refreshes_clips(tmp_path):
    from nfc_tools import manifest
    wav = recording(tmp_path)
    manifest.append(tmp_path, {"filename": wav.name, "size_bytes": wav.stat().st_size, "statuses": "birdnet=ok;nighthawk=failed"})
    report = night_status.summarize(tmp_path, config())
    assert report["files"][0]["analyzers"]["birdnet"]["analysis"] == "ok"
    assert report["pending_files"] == 1
    wav.unlink()
    assert night_status.summarize(tmp_path, config())["invalid_files"] == 1


def test_real_clip_and_csv_recovery_is_repeatable(tmp_path, monkeypatch):
    from nfc_tools.analyzers.base import AnalyzerResult
    wav = recording(tmp_path)
    original = wav.read_bytes()
    cfg = config()
    cfg.site.ebird_state_province = "MA"
    cfg.analyzers.enabled = ["nighthawk"]
    runs = []
    def run(wav, out, cfg):
        runs.append(wav)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{wav.stem}_detections.csv").write_text('start_sec,end_sec,predicted_category,prob\n1,2,amered,0.9\n')
        (out / f"{wav.stem}_audacity.txt").write_text('1\t2\tamered (0.9)\n')
        return AnalyzerResult('nighthawk', True, out)
    monkeypatch.setattr('nfc_tools.session.analyzers.get', lambda name: SimpleNamespace(run=run))
    session = Session(cfg)
    session._analyze_one(wav)
    csv_before = {p.name: p.read_bytes() for p in (tmp_path / 'eBird checklists').glob('*.csv')}
    assert csv_before
    session._analyze_one(wav, resume=True)
    assert {p.name: p.read_bytes() for p in (tmp_path / 'eBird checklists').glob('*.csv')} == csv_before
    assert len(list((tmp_path / 'clips').rglob('*.wav'))) == 1
    assert wav.read_bytes() == original
    assert len(runs) == 1
    # Lost analyzer artifacts are detected and rebuilt rather than marked complete.
    next((tmp_path / 'results').rglob('*detections.csv')).unlink()
    assert night_status.summarize(tmp_path, cfg)['pending_files'] == 1
    session._analyze_one(wav, resume=True)
    session._pool.shutdown()
    assert len(runs) == 2
    assert len(list((tmp_path / 'clips').rglob('*.wav'))) == 1


@pytest.mark.parametrize('state, count, phrase', [
    ('pending', None, 'detection status unknown'),
    ('running', None, 'detection status unknown'),
    ('failed', None, 'ANALYSIS/CLIP EXPORT FAILED'),
    ('ok', 0, 'no detections meeting review criteria'),
    ('ok', 2, 'see results and review clips'),
    ('ok', None, 'see results and review clips'),
])
def test_visible_status_distinguishes_empty_results_from_unfinished_analysis(tmp_path, state, count, phrase):
    wav = recording(tmp_path)
    cfg = config()
    progress = night_status.load_progress(tmp_path)
    entry = night_status.file_progress(tmp_path, wav, progress)
    for name in cfg.analyzers.enabled:
        entry['analyzers'][name] = dict(analysis=state, clips='ok' if state == 'ok' else 'pending')
        if count is not None:
            entry['analyzers'][name]['clip_count'] = count
    night_status.save_progress(tmp_path, progress)
    night_status.write_status_files(tmp_path, cfg)
    assert phrase in (tmp_path / 'NIGHT_STATUS.txt').read_text()
    assert phrase in (tmp_path / 'clips' / '23-59-50' / 'STATUS.txt').read_text()


def test_visible_status_reports_invalid_audio(tmp_path):
    wav = recording(tmp_path)
    wav.write_bytes(b'broken wav')
    night_status.write_status_files(tmp_path, config())
    assert 'RECORDING PROBLEM' in (tmp_path / 'NIGHT_STATUS.txt').read_text()


def test_empty_clip_export_creates_segment_folder(tmp_path):
    wav = recording(tmp_path)
    assert clip_exporter.export_analyzer_clips(wav, 'nighthawk', tmp_path / 'results', tmp_path / 'clips', config()) == 0
    assert (tmp_path / 'clips' / '23-59-50').is_dir()
