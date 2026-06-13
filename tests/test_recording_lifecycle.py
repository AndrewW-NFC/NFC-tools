import asyncio
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from nfc_tools.config import Config
from nfc_tools.session import Session
from nfc_tools.sounddevice_diagnostics import SounddevicePreviewMeter
from nfc_tools.sounddevice_recorder import SounddeviceRecorder


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
            recorder._stop_event.wait(2)

        recorder._run = ok_run

        await recorder.start()
        assert recorder._thread is not None
        assert recorder._thread.is_alive()

        await recorder.stop()
        assert recorder._thread is None

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


def test_session_resets_to_idle_when_recorder_start_fails(tmp_path, monkeypatch):
    class Weather:
        def to_dict(self):
            return {}

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
        assert session._recorder is None
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
