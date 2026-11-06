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


def colored_background(excess_db=7):
    """Synthetic control for the modest persistent excess in the Oct 13 sample."""
    rng = np.random.default_rng(20261013)
    count = 24000
    frequencies = np.fft.rfftfreq(count, 1 / 8000)
    spectrum = np.fft.rfft(rng.normal(size=count))
    spectrum[(frequencies >= 800) & (frequencies < 1400)] *= 10 ** (excess_db / 20)
    return 0.01 * np.fft.irfft(spectrum, n=count)


@pytest.mark.parametrize("gain", [0.1, 1, 3])
def test_modest_persistent_coloration_does_not_warn(gain):
    result = analyze_buzz(gain * colored_background())
    # This passes every v1 gate; it must not be treated as proof of buzz.
    assert all(w["excess_db"] >= 6 and w["bandwidth_hz"] >= 80 and w["rms_db"] >= -60
               for w in result["windows"])
    assert 6 < result["median_excess_db"] < 9
    assert not result["review_recommended"]


def test_strong_persistent_coloration_still_warns():
    assert analyze_buzz(colored_background(12))["review_recommended"]


@pytest.mark.parametrize("frequency", [50, 60])
def test_low_frequency_fft_leakage_is_not_broad_buzz(frequency):
    t = np.arange(24000) / 8000
    samples = sum(0.04 / k * np.sin(2 * np.pi * frequency * k * t) for k in range(1, 11))
    result = analyze_buzz(samples)
    # This detector does not cover mains hum: sub-800 Hz energy must not be
    # mislabeled as broad 800–1400 Hz buzz due to numerical spectral leakage.
    assert all(w["band_rms_db"] < -60 for w in result["windows"])
    assert not result["review_recommended"]


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


@pytest.mark.asyncio
async def test_colored_background_stays_ready_with_playback_and_diagnostics(tmp_path):
    from nfc_tools.readiness import _assess_test_recording, _wav_info, STATUS_READY

    path = tmp_path / "normal.wav"
    log_path = tmp_path / "normal.log"
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes((colored_background() * 32767).astype('<i2').tobytes())
    result = await _assess_test_recording({
        "wav_path": str(path), "wav_name": path.name, "wav_info": _wav_info(path),
        "download_url": "/normal.wav", "log_path": str(log_path),
    })
    assert result.status == STATUS_READY
    assert "buzz" not in result.detail.lower()
    assert result.extra["audio_url"] == "/normal.wav"
    assert not result.extra["buzz_screening"]["review_recommended"]
    assert '"median_excess_db"' in log_path.read_text()
