from types import SimpleNamespace

from nfc_tools import devices


def test_windows_directshow_devices_are_parsed(monkeypatch):
    monkeypatch.setattr(devices.platform, "system", lambda: "Windows")
    monkeypatch.setattr(devices, "ensure_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(
        devices,
        "_run",
        lambda cmd: '  "USB Audio Device" (audio)\n  "Webcam Microphone" (audio)\n',
    )

    rows = devices.list_input_devices()

    assert rows == [
        {
            "id": "dshow:USB Audio Device",
            "name": "USB Audio Device",
            "ffmpeg_input": ["-f", "dshow", "-i", "audio=USB Audio Device"],
        },
        {
            "id": "dshow:Webcam Microphone",
            "name": "Webcam Microphone",
            "ffmpeg_input": ["-f", "dshow", "-i", "audio=Webcam Microphone"],
        },
    ]


def test_linux_pulse_devices_are_parsed(monkeypatch):
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(stdout=(
            "0\talsa_output.pci-0000_00_03.0.analog-stereo.monitor\tmodule-alsa-card.c\n"
            "1\talsa_input.usb-Test_Mic.analog-stereo\tmodule-alsa-card.c\n"
        ))

    monkeypatch.setattr(devices.platform, "system", lambda: "Linux")
    monkeypatch.setattr(devices, "ensure_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(devices.subprocess, "run", fake_run)

    rows = devices.list_input_devices()

    assert rows == [
        {
            "id": "pulse:alsa_input.usb-Test_Mic.analog-stereo",
            "name": "alsa_input.usb-Test_Mic.analog-stereo",
            "ffmpeg_input": ["-f", "pulse", "-i", "alsa_input.usb-Test_Mic.analog-stereo"],
        }
    ]
