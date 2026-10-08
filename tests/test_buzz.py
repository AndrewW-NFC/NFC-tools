"""Behavioral controls for experimental, persistent-only buzz screening."""
import wave

import numpy as np
import pytest

from nfc_tools.buzz import analyze_buzz, assess_buzz


def noise(seconds=3, seed=14):
    rng = np.random.default_rng(seed)
    count = round(seconds * 8000)
    spectrum = np.fft.rfft(rng.normal(size=count))
    frequencies = np.fft.rfftfreq(count, 1 / 8000)
    spectrum[(frequencies < 800) | (frequencies >= 1400)] = 0
    buzz = np.fft.irfft(spectrum, n=count)
    return 0.04 * buzz, 0.002 * rng.normal(size=count)


@pytest.mark.parametrize("gain", [0.1, 1, 3])
def test_steady_broad_noise_is_flagged_independent_of_gain(gain):
    buzz, background = noise()
    result = analyze_buzz(gain * (buzz + background))
    assert result["review_recommended"]
    assert all(window["matches"] for window in result["windows"])


@pytest.mark.parametrize("kind", ["clean", "silence", "tone", "brief", "interrupted", "start_only", "end_only", "faint"])
def test_controls_do_not_recommend_review(kind):
    buzz, background = noise(seconds=5)
    if kind == "clean":
        samples = background
    elif kind == "silence":
        samples = np.zeros_like(buzz)
    elif kind == "tone":
        samples = background + 0.1 * np.sin(2 * np.pi * 1000 * np.arange(len(buzz)) / 8000)
    elif kind == "brief":
        buzz[:16000] = 0
        buzz[20000:] = 0
        samples = buzz + background
    elif kind == "interrupted":
        buzz[16000:24000] = 0
        samples = buzz + background
    elif kind == "start_only":
        buzz[16000:] = 0
        samples = buzz + background
    elif kind == "end_only":
        buzz[:16000] = 0
        samples = buzz + background
    else:
        samples = (buzz + background) * 0.0001
    assert not analyze_buzz(samples)["review_recommended"]


def test_fractional_end_of_clip_is_analyzed():
    buzz, background = noise(seconds=3.13)
    result = analyze_buzz(buzz + background)
    assert result["windows"][-1]["start_seconds"] == pytest.approx(2.13)


@pytest.mark.parametrize("samples", [np.zeros(8000), np.full(24000, np.nan), np.full(24000, np.inf)])
def test_unusable_audio_is_not_reported_as_a_negative(samples):
    with pytest.raises(ValueError):
        analyze_buzz(samples)


@pytest.mark.asyncio
async def test_real_decoder_and_readiness_advisory_with_diagnostics(tmp_path):
    from nfc_tools.readiness import _assess_test_recording, _wav_info, STATUS_NOTE

    buzz, background = noise()
    path = tmp_path / "sample.wav"
    log_path = tmp_path / "sample.log"
    log_path.write_text("Original recording log\n")
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(((buzz + background) * 32767).astype('<i2').tobytes())
    assert (await assess_buzz(path))["review_recommended"]
    result = await _assess_test_recording({
        "wav_path": str(path), "wav_name": path.name, "wav_info": _wav_info(path),
        "download_url": "/sample.wav", "log_path": str(log_path),
    })
    assert result.status == STATUS_NOTE
    assert "Possible steady buzz detected (experimental)" in result.detail
    assert "throughout the sample" in result.detail
    assert result.extra["audio_url"] == "/sample.wav"
    assert result.extra["buzz_screening"]["review_recommended"]
    assert log_path.read_text().startswith("Original recording log")
    assert '"windows"' in log_path.read_text()
