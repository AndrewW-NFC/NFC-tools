import asyncio
import threading
import wave
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from nfc_tools.config import Config
from nfc_tools.session import Session
from nfc_tools.sounddevice_diagnostics import SounddevicePreviewMeter
from nfc_tools.sounddevice_recorder import SounddeviceRecorder


def _write_pcm_wav(path: Path, *, frames: int, sample_rate: int = 48000, channels: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00\x00" * frames * channels)


def test_sounddevice_start_reports_thread_startup_failure(tmp_path):
    async def run():
        recorder = SounddeviceRecorder(
            device_name_hint="Missing input",
            out_dir=tmp_path,
            prefix="NFC",
            session_date=date(2026, 1, 1),
        )

        def fail_run():
            recorder._startup_error = RuntimeError("No input device")
            recorder._started_event.set()

        recorder._run = fail_run

        with pytest.raises(RuntimeError, match="failed to start"):
            await recorder.start()

        assert recorder._thread is None

    asyncio.run(run())


def test_sounddevice_start_waits_for_stream_ready_and_stops(tmp_path):
    async def run():
        recorder = SounddeviceRecorder(
            device_name_hint="Test input",
            out_dir=tmp_path,
            prefix="NFC",
            session_date=date(2026, 1, 1),
        )

        def ok_run():
            recorder._started_event.set()
            recorder._first_sample_event.set()
            recorder._stop_event.wait(2)

        recorder._run = ok_run

        await recorder.start()
        assert recorder._thread is not None
        assert recorder._thread.is_alive()

        await recorder.stop()
        assert recorder._thread is None

    asyncio.run(run())


def test_sounddevice_start_fails_when_stream_never_delivers_samples(tmp_path):
    async def run():
        recorder = SounddeviceRecorder(
            device_name_hint="Silent input",
            out_dir=tmp_path,
            prefix="NFC",
            session_date=date(2026, 1, 1),
        )

        def silent_run():
            recorder._started_event.set()
            recorder._stop_event.wait(2)

        recorder._run = silent_run

        with pytest.raises(RuntimeError, match="no audio samples arrived"):
            await recorder.start()

        assert recorder._thread is None
        assert recorder._stop_event.is_set()

    asyncio.run(run())


def test_session_threadsafe_segment_callback_runs_on_loop_thread():
    async def run():
        session = Session(Config())
        session._loop = asyncio.get_running_loop()
        loop_thread = threading.current_thread().name
        called = asyncio.Event()
        calls = []

        def fake_segment_done(wav: Path):
            calls.append((threading.current_thread().name, wav.name))
            called.set()

        session._segment_done = fake_segment_done

        worker = threading.Thread(
            target=lambda: session._segment_done_threadsafe(Path("sample.wav")),
            name="recorder-worker",
        )
        worker.start()
        await asyncio.wait_for(called.wait(), timeout=1)
        worker.join(timeout=1)

        assert calls == [(loop_thread, "sample.wav")]

    asyncio.run(run())


def test_session_defers_segment_analysis_until_stop(tmp_path):
    cfg = Config()
    cfg.power.sleep_prevention = "off"
    session = Session(cfg)
    calls = []
    wav = tmp_path / "NFC_2026-01-01_2026-01-01_21-00-00.wav"
    wav.write_bytes(b"RIFF")

    class ImmediatePool:
        def submit(self, func, *args):
            calls.append((func.__name__, args))
            return None

    session._pool = ImmediatePool()
    session._status["state"] = "recording"
    session._status["session_date"] = "2026-01-01"
    session._segment_done(wav)

    assert calls == []
    assert session.status["analysis"]["queue"] == [wav.name]

    session._start_deferred_analysis()

    assert calls == [("_drain_deferred_analysis", ())]


def test_analysis_update_can_clear_current_analyzer():
    session = Session(Config())

    session._analysis_update(active=True, current_file="sample.wav", current_analyzer="birdnet")
    assert session.status["analysis"]["current_analyzer"] == "birdnet"

    session._analysis_update(active=False, current_analyzer=None)
    assert session.status["analysis"]["active"] is False
    assert session.status["analysis"]["current_analyzer"] is None


def test_recording_integrity_accepts_readable_wav(tmp_path):
    session = Session(Config())
    wav = tmp_path / "2026-01-01" / "audio" / "valid.wav"
    _write_pcm_wav(wav, frames=48000)

    result = session._check_recording_integrity(wav)

    assert result.status == "valid"
    assert result.ok_to_analyze is True
    assert result.duration_seconds == pytest.approx(1.0)
    assert result.sample_rate == 48000
    assert result.channels == 1


def test_recording_integrity_flags_too_short_wav_as_suspicious(tmp_path):
    session = Session(Config())
    wav = tmp_path / "2026-01-01" / "audio" / "short.wav"
    _write_pcm_wav(wav, frames=1200)

    result = session._check_recording_integrity(wav)

    assert result.status == "suspicious"
    assert result.ok_to_analyze is True
    assert "very short" in result.message


def test_recording_integrity_skips_empty_file(tmp_path):
    session = Session(Config())
    wav = tmp_path / "2026-01-01" / "audio" / "empty.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    wav.write_bytes(b"")

    result = session._check_recording_integrity(wav)

    assert result.status == "skipped"
    assert result.ok_to_analyze is False
    assert "empty" in result.message


def test_deferred_analysis_skips_unreadable_recording(tmp_path):
    cfg = Config()
    cfg.analyzers.enabled = ["birdnet"]
    session = Session(cfg)
    wav = tmp_path / "2026-01-01" / "audio" / "broken.wav"
    wav.parent.mkdir(parents=True, exist_ok=True)
    wav.write_bytes(b"not a wave")
    analyzed = []

    session._status["analysis"]["queue"] = [wav.name]
    session._pending_analysis_paths = [wav]
    session._analysis_drain_running = True
    session._analyze_one = lambda path: analyzed.append(path)

    session._drain_deferred_analysis()

    assert analyzed == []
    assert session.status["analysis"]["queue"] == []
    assert "Analysis skipped" in session.status["analysis"]["message"]
    assert any(row["event"] == "recording_integrity_failed" for row in session.status["session_log"])


def test_session_holds_sleep_prevention_while_recording(tmp_path, monkeypatch):
    class Weather:
        def to_dict(self):
            return {}

    class FakeSleepPreventer:
        instances = []

        def __init__(self):
            self.calls = []
            FakeSleepPreventer.instances.append(self)

        def start(self):
            self.calls.append("start")
            return {"sleep_prevention_active": True, "sleep_prevention_mode": "test"}

        def stop(self):
            self.calls.append("stop")
            return {"sleep_prevention_active": False, "sleep_prevention_mode": "off"}

    class FakeRecorder:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.stopped = False

        async def start(self):
            return None

        async def stop(self):
            self.stopped = True

        def diagnostics_info(self):
            return {"recording_backend": "ffmpeg", "ffmpeg_log": "test.log"}

    def fake_night_dir(session_date: str) -> Path:
        path = tmp_path / session_date
        (path / "audio").mkdir(parents=True, exist_ok=True)
        (path / "results").mkdir(parents=True, exist_ok=True)
        (path / "logs").mkdir(parents=True, exist_ok=True)
        return path

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "night_dir", fake_night_dir)
    monkeypatch.setattr(session_mod, "snapshot", lambda *args: Weather())
    monkeypatch.setattr(session_mod, "SleepPreventer", FakeSleepPreventer)
    monkeypatch.setattr(session_mod, "Recorder", FakeRecorder)

    async def run():
        cfg = Config()
        cfg.recording.device = "test"
        session = Session(cfg)
        session._loop = asyncio.get_running_loop()
        session._resolve_device_record = lambda: {
            "id": "test",
            "name": "Test microphone",
            "ffmpeg_input": ["dummy"],
        }
        session._select_recording_backend = lambda: "ffmpeg"
        session._start_deferred_analysis = lambda: None

        start = datetime(2026, 1, 1, 21, 0)
        end = start + timedelta(hours=1)
        await session._begin_recording(date(2026, 1, 1), start, end)

        assert session.status["power"]["sleep_prevention_active"] is True
        assert any(row["event"] == "sleep_prevention_started" for row in session.status["session_log"])

        await session.stop("user")

        assert session.status["power"]["sleep_prevention_active"] is False
        assert FakeSleepPreventer.instances[0].calls == ["start", "stop"]
        assert any(row["event"] == "sleep_prevention_stopped" for row in session.status["session_log"])

    asyncio.run(run())


def test_session_keeps_sleep_prevention_when_analysis_starts():
    class FakeSleepPreventer:
        def __init__(self):
            self.calls = []

        def stop(self):
            self.calls.append("stop")
            return {"sleep_prevention_active": False, "sleep_prevention_mode": "off"}

    class FakeRecorder:
        async def stop(self):
            return None

    async def run():
        session = Session(Config())
        sleep = FakeSleepPreventer()
        session._sleep_preventer = sleep
        session._status["state"] = "recording"
        session._status["power"] = {"sleep_prevention_active": True}
        session._recorder = FakeRecorder()
        session._start_deferred_analysis = lambda: True

        await session.stop("schedule")

        assert sleep.calls == []
        assert session.status["power"]["sleep_prevention_active"] is True

    asyncio.run(run())


def test_analysis_drain_releases_sleep_prevention_after_queue_finishes(tmp_path):
    class FakeSleepPreventer:
        def __init__(self):
            self.calls = []

        def stop(self):
            self.calls.append("stop")
            return {"sleep_prevention_active": False, "sleep_prevention_mode": "off"}

    session = Session(Config())
    sleep = FakeSleepPreventer()
    wav = tmp_path / "2026-01-01" / "audio" / "valid.wav"
    _write_pcm_wav(wav, frames=48000)
    analyzed = []

    session._sleep_preventer = sleep
    session._status["power"] = {"sleep_prevention_active": True}
    session._pending_analysis_paths = [wav]
    session._analysis_drain_running = True
    session._status["analysis"]["queue"] = [wav.name]
    session._analyze_one = lambda path: analyzed.append(path)

    session._drain_deferred_analysis()

    assert analyzed == [wav]
    assert sleep.calls == ["stop"]
    assert session.status["power"]["sleep_prevention_active"] is False
    assert any(row["event"] == "sleep_prevention_stopped" for row in session.status["session_log"])


def test_analysis_defers_on_battery_policy(tmp_path, monkeypatch):
    class Snapshot:
        def to_dict(self):
            return {
                "power_source_available": True,
                "power_source": "battery",
                "on_battery": True,
                "battery_percent": 82,
                "power_platform": "test",
                "power_details": "",
            }

    class FakeSleepPreventer:
        active = True

        def __init__(self):
            self.calls = []

        def stop(self):
            self.calls.append("stop")
            self.active = False
            return {"sleep_prevention_active": False, "sleep_prevention_mode": "off"}

        def status(self):
            return {"sleep_prevention_active": self.active, "sleep_prevention_mode": "test"}

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "current_power_snapshot", lambda: Snapshot())

    cfg = Config()
    cfg.power.analysis_policy = "defer_on_battery"
    session = Session(cfg)
    sleep = FakeSleepPreventer()
    wav = tmp_path / "2026-01-01" / "audio" / "valid.wav"
    _write_pcm_wav(wav, frames=48000)

    session._sleep_preventer = sleep
    session._pending_analysis_paths = [wav]
    session._status["analysis"]["queue"] = [wav.name]

    started = session._start_deferred_analysis()

    assert started is False
    assert session._pending_analysis_paths == [wav]
    assert sleep.calls == ["stop"]
    assert "deferred" in session.status["analysis"]["message"].lower()
    assert any(row["event"] == "analysis_deferred_power" for row in session.status["session_log"])


def test_forced_pending_analysis_ignores_battery_deferral(tmp_path, monkeypatch):
    class Snapshot:
        def to_dict(self):
            return {
                "power_source_available": True,
                "power_source": "battery",
                "on_battery": True,
                "battery_percent": 10,
                "power_platform": "test",
                "power_details": "",
            }

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "current_power_snapshot", lambda: Snapshot())

    cfg = Config()
    cfg.power.analysis_policy = "defer_on_battery"
    cfg.power.sleep_prevention = "off"
    session = Session(cfg)
    calls = []
    wav = tmp_path / "2026-01-01" / "audio" / "valid.wav"
    _write_pcm_wav(wav, frames=48000)

    class ImmediatePool:
        def submit(self, func, *args):
            calls.append((func.__name__, args))
            return None

    session._pool = ImmediatePool()
    session._pending_analysis_paths = [wav]

    started = session.start_pending_analysis(force=True)

    assert started is True
    assert calls == [("_drain_deferred_analysis", ())]


def test_low_battery_warning_logs_once(monkeypatch):
    class Snapshot:
        def to_dict(self):
            return {
                "power_source_available": True,
                "power_source": "battery",
                "on_battery": True,
                "battery_percent": 12,
                "power_platform": "test",
                "power_details": "",
            }

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "current_power_snapshot", lambda: Snapshot())

    cfg = Config()
    cfg.power.low_battery_warning_percent = 20
    session = Session(cfg)

    session._maybe_log_low_battery()
    session._maybe_log_low_battery()

    events = [row["event"] for row in session.status["session_log"]]
    assert events.count("low_battery_warning") == 1


def test_critical_battery_stops_recording_and_defers_analysis(tmp_path, monkeypatch):
    class Snapshot:
        def to_dict(self):
            return {
                "power_source_available": True,
                "power_source": "battery",
                "on_battery": True,
                "battery_percent": 5,
                "power_platform": "test",
                "power_details": "",
            }

    class FakeRecorder:
        def __init__(self):
            self.stopped = False

        async def stop(self):
            self.stopped = True

    class FakeSleepPreventer:
        active = True

        def __init__(self):
            self.calls = []

        def stop(self):
            self.calls.append("stop")
            self.active = False
            return {"sleep_prevention_active": False, "sleep_prevention_mode": "off"}

        def status(self):
            return {"sleep_prevention_active": self.active, "sleep_prevention_mode": "test"}

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "current_power_snapshot", lambda: Snapshot())

    async def run():
        cfg = Config()
        cfg.power.critical_battery_percent = 10
        cfg.power.critical_battery_action = "stop_recording_defer_analysis"
        session = Session(cfg)
        recorder = FakeRecorder()
        sleep = FakeSleepPreventer()
        wav = tmp_path / "2026-01-01" / "audio" / "valid.wav"
        _write_pcm_wav(wav, frames=48000)

        session._sleep_preventer = sleep
        session._status["state"] = "recording"
        session._status["power"] = {"sleep_prevention_active": True}
        session._recorder = recorder
        session._pending_analysis_paths = [wav]
        session._status["analysis"]["queue"] = [wav.name]

        acted = await session._maybe_take_critical_battery_action()

        assert acted is True
        assert recorder.stopped is True
        assert session.status["state"] == "idle"
        assert session._pending_analysis_paths == [wav]
        assert "critical threshold" in session.status["analysis"]["message"]
        events = [row["event"] for row in session.status["session_log"]]
        assert "critical_battery_stop" in events
        assert "analysis_deferred_power" in events
        assert "sleep_prevention_stopped" in events

    asyncio.run(run())


def test_critical_battery_can_defer_analysis_without_stopping(monkeypatch):
    class Snapshot:
        def to_dict(self):
            return {
                "power_source_available": True,
                "power_source": "battery",
                "on_battery": True,
                "battery_percent": 7,
                "power_platform": "test",
                "power_details": "",
            }

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "current_power_snapshot", lambda: Snapshot())

    async def run():
        cfg = Config()
        cfg.power.critical_battery_percent = 10
        cfg.power.critical_battery_action = "defer_analysis"
        session = Session(cfg)
        session._status["state"] = "recording"

        acted = await session._maybe_take_critical_battery_action()

        assert acted is False
        assert session.status["state"] == "recording"
        assert session._analysis_deferred_reason is not None
        assert any(row["event"] == "critical_battery_defer_analysis" for row in session.status["session_log"])

    asyncio.run(run())


def test_session_resets_to_idle_when_recorder_start_fails(tmp_path, monkeypatch):
    class Weather:
        def to_dict(self):
            return {}

    class FakeSleepPreventer:
        instances = []

        def __init__(self):
            self.calls = []
            FakeSleepPreventer.instances.append(self)

        def start(self):
            self.calls.append("start")
            return {"sleep_prevention_active": True, "sleep_prevention_mode": "test"}

        def stop(self):
            self.calls.append("stop")
            return {"sleep_prevention_active": False, "sleep_prevention_mode": "off"}

    class FailingRecorder:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def start(self):
            raise RuntimeError("no stream")

        def diagnostics_info(self):
            return {"recording_backend": "sounddevice_coreaudio", "sounddevice_log": "test.log"}

    def fake_night_dir(session_date: str) -> Path:
        path = tmp_path / session_date
        (path / "audio").mkdir(parents=True, exist_ok=True)
        (path / "results").mkdir(parents=True, exist_ok=True)
        (path / "logs").mkdir(parents=True, exist_ok=True)
        return path

    import nfc_tools.session as session_mod

    monkeypatch.setattr(session_mod, "night_dir", fake_night_dir)
    monkeypatch.setattr(session_mod, "snapshot", lambda *args: Weather())
    monkeypatch.setattr(session_mod, "SleepPreventer", FakeSleepPreventer)
    monkeypatch.setattr(session_mod, "SounddeviceRecorder", FailingRecorder)

    async def run():
        cfg = Config()
        cfg.recording.device = "test"
        session = Session(cfg)
        session._loop = asyncio.get_running_loop()
        session._resolve_device_record = lambda: {
            "id": "test",
            "name": "Test microphone",
            "ffmpeg_input": ["dummy"],
        }
        session._select_recording_backend = lambda: "sounddevice"

        start = datetime(2026, 1, 1, 21, 0)
        end = start + timedelta(hours=1)
        with pytest.raises(RuntimeError, match="Recording failed to start"):
            await session._begin_recording(date(2026, 1, 1), start, end)

        assert session.status["state"] == "idle"
        assert session.status["power"]["sleep_prevention_active"] is False
        assert session._recorder is None
        assert FakeSleepPreventer.instances[0].calls == ["start", "stop"]
        assert any(row["event"] == "recording_failed" for row in session.status["session_log"])

    asyncio.run(run())


def test_sounddevice_preview_meter_returns_latest_sample_copy():
    meter = SounddevicePreviewMeter()

    def fake_ensure_stream(config):
        meter._config = config
        meter._started_event.set()
        meter._sample_event.set()
        meter._latest = {
            "source": "sounddevice_coreaudio_preview",
            "recording": False,
            "sample_rate": config[0],
            "channels": config[1],
            "device_index": 0,
            "device_name": "Test microphone",
            "rms": 0.25,
            "peak": 0.5,
            "rms_db": -12.0,
            "peak_db": -6.0,
            "level_db": -12.0,
            "near_full_scale_fraction": 0.0,
        }

    meter._ensure_stream = fake_ensure_stream

    first = meter.measure(sample_rate=48000, channels=1, selected_name="Test microphone")
    first["rms_db"] = -99.0
    second = meter.measure(sample_rate=48000, channels=1, selected_name="Test microphone")

    assert second["rms_db"] == -12.0
    assert second["device_name"] == "Test microphone"
