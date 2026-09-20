import io

import numpy as np
import pytest

from nfc_tools.analyzers.wingbeat_accompaniment import (
    ANALYSIS_RATE,
    accompaniment_features,
    screen_accompaniment,
)
from nfc_tools.analyzers.wingbeats import detect_stream, screen_window


def whistle(seed=0, frequency=5432.1, kind='accompanied'):
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    pulse = .03 + np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    noise = np.random.default_rng(seed).normal(0, 1, len(t))
    tone = .2 * np.sin(2 * np.pi * frequency * t) * pulse
    if kind == 'stationary':
        return tone + .015 * noise
    if kind == 'tone':
        return tone
    if kind == 'harmonics':
        return tone + .1 * np.sin(2 * np.pi * frequency / 2 * t) * pulse
    if kind == 'sweep':
        return .2 * np.sin(2 * np.pi * (3500 * t + 1000 * t * t)) * pulse + .002 * noise
    return tone + .04 * noise * pulse


@pytest.mark.parametrize('frequency', [1532.1, 2732.1, 5432.1, 7832.1])
@pytest.mark.parametrize('seed', range(5))
def test_detects_whistle_with_softer_synchronous_noise(frequency, seed):
    samples = whistle(seed, frequency)
    assert screen_accompaniment(accompaniment_features(samples)) is not None
    assert screen_window(samples, ANALYSIS_RATE) is not None


@pytest.mark.parametrize('kind', ['tone', 'stationary', 'harmonics', 'sweep'])
@pytest.mark.parametrize('frequency', [1532.1, 2732.1, 5432.1, 7832.1])
def test_rejects_tonal_leakage_and_unrelated_background(kind, frequency):
    # Off-bin frequencies and multiple harmonics must not simulate air noise.
    samples = whistle(frequency=frequency, kind=kind)
    assert screen_accompaniment(accompaniment_features(samples)) is None
    assert screen_window(samples, ANALYSIS_RATE) is None


def test_opposite_noise_is_not_synchronous_with_whistle():
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    pulse = np.maximum(0, np.sin(2 * np.pi * 7 * t)) ** 4
    noise = np.random.default_rng(0).normal(0, .04, len(t))
    samples = .2 * np.sin(2 * np.pi * 5432.1 * t) * (.03 + pulse) + noise * (1 - pulse)
    feature = next(item for item in accompaniment_features(samples) if item.lower_hz == 3500)
    assert feature.noise_coherence < 0
    assert screen_accompaniment([feature]) is None
    # Other bands contain genuinely pulsed noise, so the full screen may flag it.


@pytest.mark.parametrize('gain', [.1, 1, 3])
def test_stream_uses_explicit_wideband_rate_and_merges(gain):
    samples = np.tile(whistle(), 3).astype('<f4') * gain
    detections = detect_stream(io.BytesIO(samples.tobytes()), ANALYSIS_RATE)
    assert len(detections) == 1
    assert detections[0].start == 0
    assert detections[0].end == 6


@pytest.mark.parametrize('samples', [np.zeros(48000), np.full(48000, np.nan), np.zeros(100)])
def test_invalid_or_empty_signal(samples):
    assert screen_window(samples, ANALYSIS_RATE) is None


def test_soft_whistle_and_accompaniment_survive_low_frequency_background():
    t = np.arange(2 * ANALYSIS_RATE) / ANALYSIS_RATE
    samples = whistle() * .1 + .15 * np.sin(2 * np.pi * 200 * t)
    assert screen_accompaniment(accompaniment_features(samples)) is not None


def test_plugin_decodes_high_frequency_accompaniment(tmp_path):
    import wave

    from nfc_tools.analyzers.wingbeats import WingbeatsPlugin
    from nfc_tools.config import Config

    path = tmp_path / 'high-whistle.wav'
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(ANALYSIS_RATE)
        audio.writeframes((whistle() * 32767).astype('<i2').tobytes())
    result = WingbeatsPlugin().run(path, tmp_path / 'output', Config())
    assert result.success, result.message
    assert result.detections_count == 1


@pytest.mark.parametrize('start_hz', [1500, 4500, 6500])
def test_high_sweep_leakage_cannot_trigger_low_band_route(start_hz):
    t = np.arange(4 * ANALYSIS_RATE) / ANALYSIS_RATE
    signal = .2 * np.sin(2 * np.pi * (start_hz * t + 500 * t * t))
    signal *= .1 + np.maximum(0, np.sin(2 * np.pi * 7 * t))
    assert not detect_stream(io.BytesIO(signal.astype('<f4').tobytes()), ANALYSIS_RATE)
