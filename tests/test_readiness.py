from nfc_tools.readiness import (
    STATUS_NOT_CHECKED,
    STATUS_NOTE,
    STATUS_READY,
    ReadinessCheck,
    _check_power,
    grouped_results,
    initial_readiness_groups,
)
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
