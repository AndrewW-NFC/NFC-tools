"""Protect external-first selection and prevent silent internal-mic fallback."""
from types import SimpleNamespace

import pytest

from nfc_tools.devices import input_kind, resolve_input_device
from nfc_tools.sounddevice_common import choose_input_device


def device(name, index=0):
    return {"id": f"avfoundation:{index}", "name": name,
            "ffmpeg_input": ["-f", "avfoundation", "-i", f":{index}"]}


@pytest.mark.parametrize("selection", [None, "auto_external", "avfoundation:0"])
@pytest.mark.parametrize("external_index", [0, 2, 7])
def test_auto_selects_connected_external_regardless_of_old_index(selection, external_index):
    external = device("External Microphone", external_index)
    available = [device("MacBook Air Microphone", 4), device("Quiet Comfort 35", 1), external]
    assert resolve_input_device(selection, available) is external


@pytest.mark.parametrize("name", ["USB Audio Device", "External Microphone", "AudioMoth",
                                  "alsa_input.usb-Test_Mic.analog-stereo"])
def test_recognizes_external_inputs(name):
    assert input_kind(device(name)) == "external"


@pytest.mark.parametrize("name", ["MacBook Air Microphone", "Built-in Microphone",
    "Microphone Array (Realtek Audio)", "USB Webcam Microphone", "USB Headset",
    "QuietComfort 35", "Quiet Comfort 35", "AirPods", "bluez_input.00.01"])
def test_unsuitable_inputs_require_explicit_selection(name):
    mic = device(name)
    with pytest.raises(RuntimeError, match="No suitable external"):
        resolve_input_device(None, [mic])
    assert resolve_input_device("name:" + name, [mic]) is mic


@pytest.mark.parametrize("available", [[], [device("MacBook Air Microphone")]])
def test_no_external_input_stops_instead_of_falling_back(available):
    with pytest.raises(RuntimeError, match="No suitable external"):
        resolve_input_device("avfoundation:0", available)


def test_multiple_or_unknown_inputs_require_explicit_selection():
    usb, external, unknown = device("USB Mic", 1), device("External Microphone", 2), device("Field Recorder", 3)
    for available in ([usb, external], [unknown], [usb, unknown]):
        with pytest.raises(RuntimeError, match="Choose an external microphone"):
            resolve_input_device(None, available)
    assert resolve_input_device("name:Field Recorder", [usb, unknown]) is unknown
    assert resolve_input_device("name:USB Mic", [external, usb]) is usb


def test_explicit_selection_tracks_name_and_never_substitutes_another_input():
    wanted = device("USB Mic", 7)
    assert resolve_input_device("name:USB Mic", [device("External Microphone"), wanted]) is wanted
    for available in ([device("External Microphone")], [wanted, device("USB Mic", 8)]):
        with pytest.raises(RuntimeError, match="missing or ambiguous"):
            resolve_input_device("name:USB Mic", available)


def sounddevice(names):
    return SimpleNamespace(query_devices=lambda: [dict(name=name, max_input_channels=1) for name in names],
                           default=SimpleNamespace(device=(0, 0)))


def test_backend_resolves_exact_name_after_device_reordering():
    sd = sounddevice(["MacBook Air Microphone", "USB Mic Pro", "USB Mic"])
    assert choose_input_device(sd, "USB Mic") == 2


@pytest.mark.parametrize("selection,names", [
    ("USB Mic", ["MacBook Air Microphone"]),
    ("USB Mic", ["MacBook Air Microphone", "USB Mic Pro"]),
    ("USB Mic", ["USB Mic", "USB Mic"]),
    (None, ["MacBook Air Microphone"]),
])
def test_backend_never_falls_back_to_default(selection, names):
    with pytest.raises(RuntimeError, match="will not fall back"):
        choose_input_device(sounddevice(names), selection)


def test_session_readiness_and_diagnostics_share_external_selection(monkeypatch):
    from nfc_tools.config import Config
    from nfc_tools import session, readiness, doctor
    from nfc_tools.web import routes_diagnostics
    cfg = Config()
    cfg.recording.device = "avfoundation:0"
    external = device("External Microphone", 2)
    for module in (session, readiness, doctor, routes_diagnostics):
        monkeypatch.setattr(module, "list_input_devices", lambda: [device("MacBook Air Microphone"), external])
    monkeypatch.setattr(routes_diagnostics.state, "cfg", cfg)
    assert session.Session(cfg)._resolve_device_record() is external
    assert readiness._configured_device(cfg) is external
    assert routes_diagnostics._recording_test_device_record() is external
    assert "External Microphone" in doctor._check_devices(cfg).detail


def test_settings_allows_and_saves_unsuitable_microphone(monkeypatch):
    from html.parser import HTMLParser
    from fastapi.testclient import TestClient
    from nfc_tools.config import Config
    from nfc_tools.web import routes
    from nfc_tools.web.server import create_app

    mic = device("Built-in Microphone")
    cfg = Config()
    saved = []
    monkeypatch.setattr(routes.state, "cfg", cfg)
    monkeypatch.setattr(routes, "list_input_devices", lambda: [mic])
    monkeypatch.setattr(routes.installer, "status", lambda: {
        name: {"installed": False} for name in ("ffmpeg", "birdnet", "nighthawk", "wingbeats")
    })
    monkeypatch.setattr(routes.config_mod, "save", lambda value: saved.append(value))
    monkeypatch.setattr(routes, "timezone_for_coordinates", lambda lat, lon: "America/New_York")
    client = TestClient(create_app())
    response = client.post("/settings/save", data={"device_id": "name:Built-in Microphone"},
                           follow_redirects=False)
    assert response.status_code == 303
    assert saved[-1].recording.device == "name:Built-in Microphone"
    response = client.get("/settings")
    assert response.status_code == 200

    class Options(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag == "option":
                options.append(dict(attrs))

    options = []
    Options().feed(response.text)
    option = next(item for item in options if item.get("value") == "name:Built-in Microphone")
    assert "disabled" not in option
    assert "selected" in option
    assert "Built-in Microphone — not suitable" in response.text
    assert resolve_input_device(saved[-1].recording.device, [mic]) is mic
