import math
import struct
import wave

import pytest

from nfc_tools.readiness import (
    STATUS_NOT_CHECKED,
    STATUS_NOTE,
    STATUS_READY,
    STATUS_PROBLEM,
    _assess_test_recording,
    _wav_info,
    ReadinessCheck,
    _check_ebird_state_province,
    _check_power,
    grouped_results,
    initial_readiness_groups,
)
from nfc_tools.config import Config
from nfc_tools.power import PowerSnapshot


def test_initial_readiness_groups_are_neutral_and_ordered():
    groups = initial_readiness_groups()

    assert [group["title"] for group in groups] == [
        "Recording Input",
        "Storage",
        "Overnight Reliability",
        "Supporting Services",
    ]
    assert groups[0]["checks"][0]["label"] == "Configured microphone is available and can be opened."
    assert groups[0]["checks"][1]["label"] == "Input signal is present."
    assert groups[0]["checks"][2]["label"] == "Test recording produces usable audio."
    supporting_checks = [check["id"] for check in groups[3]["checks"]]
    assert supporting_checks == ["analyzers", "environment_logging", "ebird_state_province"]
    assert all(check["status"] == STATUS_NOT_CHECKED for group in groups for check in group["checks"])


def test_grouped_results_preserve_layout_and_apply_statuses():
    groups = grouped_results([
        ReadinessCheck("microphone_open", STATUS_READY, "Opened Test mic."),
    ])

    first = groups[0]["checks"][0]
    second = groups[0]["checks"][1]
    assert first["status"] == STATUS_READY
    assert first["detail"] == "Opened Test mic."
    assert second["status"] == STATUS_NOT_CHECKED


def test_power_note_explains_why_battery_is_flagged(monkeypatch):
    monkeypatch.setattr(
        "nfc_tools.readiness.current_power_snapshot",
        lambda: PowerSnapshot(True, "battery", True, 76, "TestOS", ""),
    )

    check = _check_power()

    assert check.status == STATUS_NOTE
    assert "Computer is running on battery (76% battery)." in check.detail
    assert "Flagged because battery-powered recording may not last overnight." in check.detail


def test_ebird_state_province_ready_when_configured():
    cfg = Config()
    cfg.site.ebird_state_province = "MA"

    check = _check_ebird_state_province(cfg)

    assert check.status == STATUS_READY
    assert "MA" in check.detail
    assert "exports will use" in check.detail


def test_ebird_state_province_note_when_missing():
    cfg = Config()
    cfg.site.ebird_state_province = ""

    check = _check_ebird_state_province(cfg)

    assert check.status == STATUS_READY
    assert "eBird exports not requested" in check.detail


def _sample_result(path):
    return {
        "wav_path": str(path), "wav_name": path.name,
        "wav_info": _wav_info(path),
        "download_url": "/sample.wav", "log_download_url": "/sample.log",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("amplitude,status,phrase", [
    (0, STATUS_PROBLEM, "silent or nearly silent"),
    (0.0005, STATUS_NOTE, "Input volume is very low"),
    (0.1, STATUS_READY, "above the low-level warning threshold"),
])
async def test_saved_sample_levels_with_real_ffmpeg(tmp_path, amplitude, status, phrase):
    path = tmp_path / "sample.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"".join(struct.pack("<h", round(
            32767 * amplitude * math.sin(2 * math.pi * 440 * i / 8000)
        )) for i in range(24000)))
    check = await _assess_test_recording(_sample_result(path))
    assert check.status == status
    assert phrase in check.detail
    assert check.extra["audio_url"] == "/sample.wav"
    assert path.exists()


@pytest.mark.asyncio
async def test_level_measurement_failure_keeps_sample(monkeypatch):
    async def fail(*args, **kwargs):
        raise RuntimeError("decoder failed")
    monkeypatch.setattr("nfc_tools.readiness.measure_levels", fail)
    check = await _assess_test_recording({
        "wav_path": "sample.wav", "wav_name": "sample.wav",
        "wav_info": {"duration_seconds": 3, "sample_rate": 48000, "channels": 1},
        "download_url": "/sample.wav",
    })
    assert check.status == STATUS_NOTE
    assert "could not be checked automatically" in check.detail
    assert check.extra["audio_url"] == "/sample.wav"


@pytest.mark.asyncio
async def test_brief_peak_does_not_hide_low_average_input(monkeypatch):
    async def levels(*args, **kwargs):
        return {"returncode": 0, "mean_db": -65, "peak_db": -20}
    monkeypatch.setattr("nfc_tools.readiness.measure_levels", levels)
    check = await _assess_test_recording({
        "wav_path": "sample.wav", "wav_name": "sample.wav",
        "wav_info": {"duration_seconds": 3, "sample_rate": 48000, "channels": 1},
        "download_url": "/sample.wav",
    })
    assert check.status == STATUS_NOTE
    assert "very low" in check.detail
