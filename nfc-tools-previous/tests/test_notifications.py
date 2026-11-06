import wave
from pathlib import Path

from nfc_tools import notifications


def test_bundled_chime_is_playable_pcm():
    path = Path(notifications.__file__).parent / 'data/sounds/slow-ding.wav'
    with wave.open(str(path), 'rb') as audio:
        assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (1, 2, 44100)
        assert 2 < audio.getnframes() / audio.getframerate() < 5


def test_playback_failure_is_nonfatal(monkeypatch):
    class ImmediateThread:
        def __init__(self, *, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    attempted = []

    def fail(*args, **kwargs):
        attempted.append(args)
        raise OSError('No audio output available')

    monkeypatch.setattr(notifications.threading, 'Thread', ImmediateThread)
    monkeypatch.setattr(notifications.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(notifications.subprocess, 'run', fail)
    notifications.play_completion_chime()
    assert len(attempted) == 1
