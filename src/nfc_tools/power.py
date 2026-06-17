"""Cross-platform power source and sleep-prevention helpers."""
from __future__ import annotations

import ctypes
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .logging_setup import get

log = get("power")


@dataclass
class PowerSnapshot:
    available: bool
    power_source: str = "unknown"
    on_battery: bool | None = None
    battery_percent: int | None = None
    platform: str = ""
    details: str = ""

    def to_dict(self) -> dict:
        return {
            "power_source_available": self.available,
            "power_source": self.power_source,
            "on_battery": self.on_battery,
            "battery_percent": self.battery_percent,
            "power_platform": self.platform,
            "power_details": self.details,
        }


class SleepPreventer:
    """Hold an OS idle-sleep assertion while recording or analyzing.

    The platform implementations intentionally avoid forcing the display to
    remain on. The goal is to keep work running while still allowing a dimmed or
    sleeping screen to conserve battery.
    """

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._command: list[str] = []
        self._mode = "off"
        self._message = "Sleep prevention is off."
        self._windows_active = False

    @property
    def active(self) -> bool:
        if self._windows_active:
            return True
        return self._process is not None and self._process.poll() is None

    def start(self) -> dict:
        if self.active:
            return self.status()

        system = platform.system()
        if system == "Darwin":
            executable = shutil.which("caffeinate")
            if not executable:
                self._mode = "unavailable"
                self._message = "macOS caffeinate command was not found."
                return self.status(active=False)
            return self._start_process(
                [executable, "-i", "-m"],
                mode="macos_caffeinate_idle",
                message="Mac idle sleep is blocked while recording or analyzing; the display may still sleep.",
            )
        if system == "Windows":
            return self._start_windows()
        if system == "Linux":
            inhibitor = shutil.which("systemd-inhibit")
            if inhibitor:
                return self._start_process(
                    [
                        inhibitor,
                        "--what=idle:sleep",
                        "--why=NFC Tools recording or analysis",
                        "--mode=block",
                        sys.executable,
                        "-c",
                        "import time; time.sleep(10**9)",
                    ],
                    mode="linux_systemd_inhibit",
                    message="Linux idle sleep is blocked while recording or analyzing; the display may still sleep.",
                )

        self._mode = "unavailable"
        self._message = f"Sleep prevention is not available on this {system or 'unknown'} system."
        return self.status(active=False)

    def stop(self) -> dict:
        if self._windows_active:
            self._release_windows()

        proc = self._process
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        self._process = None
        self._mode = "off"
        self._message = "Sleep prevention is off."
        return self.status(active=False)

    def status(self, *, active: bool | None = None) -> dict:
        is_active = self.active if active is None else active
        mode = self._mode if is_active or self._mode in {"unavailable", "error"} else "off"
        message = self._message if is_active or self._mode in {"unavailable", "error"} else "Sleep prevention is off."
        return {
            "sleep_prevention_active": is_active,
            "sleep_prevention_mode": mode,
            "sleep_prevention_command": " ".join(self._command) if self._command else "",
            "sleep_prevention_message": message,
        }

    def _start_process(self, command: list[str], *, mode: str, message: str) -> dict:
        if not command[0]:
            self._mode = "unavailable"
            self._message = "Sleep prevention command was not found."
            return self.status(active=False)

        self._command = command
        try:
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to start sleep prevention: %s", exc)
            self._process = None
            self._mode = "error"
            self._message = f"Could not start sleep prevention: {exc}"
            return self.status(active=False)

        self._mode = mode
        self._message = message
        return self.status()

    def _start_windows(self) -> dict:
        try:
            kernel32 = ctypes.windll.kernel32
            es_continuous = 0x80000000
            es_system_required = 0x00000001
            result = kernel32.SetThreadExecutionState(es_continuous | es_system_required)
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to start Windows sleep prevention: %s", exc)
            self._mode = "error"
            self._message = f"Could not start Windows sleep prevention: {exc}"
            return self.status(active=False)

        if result == 0:
            self._mode = "error"
            self._message = "Windows rejected the sleep-prevention request."
            return self.status(active=False)

        self._windows_active = True
        self._command = ["SetThreadExecutionState", "ES_CONTINUOUS|ES_SYSTEM_REQUIRED"]
        self._mode = "windows_execution_state"
        self._message = "Windows idle sleep is blocked while recording or analyzing; the display may still sleep."
        return self.status()

    def _release_windows(self) -> None:
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception as exc:  # noqa: BLE001
            log.warning("failed to release Windows sleep prevention: %s", exc)
        self._windows_active = False


def current_power_snapshot() -> PowerSnapshot:
    system = platform.system()
    if system == "Darwin":
        return _macos_power_snapshot()
    if system == "Windows":
        return _windows_power_snapshot()
    if system == "Linux":
        return _linux_power_snapshot()
    return PowerSnapshot(False, platform=system, details="Unsupported platform.")


def _macos_power_snapshot() -> PowerSnapshot:
    try:
        out = subprocess.check_output(["pmset", "-g", "batt"], text=True, timeout=5)
    except Exception as exc:  # noqa: BLE001
        return PowerSnapshot(False, platform="Darwin", details=str(exc))

    percent_match = re.search(r"(\d+)%", out)
    percent = int(percent_match.group(1)) if percent_match else None
    on_battery = "Battery Power" in out
    source = "battery" if on_battery else "ac" if "AC Power" in out else "unknown"
    return PowerSnapshot(True, source, on_battery, percent, "Darwin", out.strip())


def _windows_power_snapshot() -> PowerSnapshot:
    class SystemPowerStatus(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SystemPowerStatus()
    try:
        ok = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status))
    except Exception as exc:  # noqa: BLE001
        return PowerSnapshot(False, platform="Windows", details=str(exc))
    if not ok:
        return PowerSnapshot(False, platform="Windows", details="GetSystemPowerStatus failed.")

    ac_status = int(status.ACLineStatus)
    percent_raw = int(status.BatteryLifePercent)
    percent = None if percent_raw == 255 else percent_raw
    on_battery = True if ac_status == 0 else False if ac_status == 1 else None
    source = "battery" if on_battery else "ac" if on_battery is False else "unknown"
    return PowerSnapshot(True, source, on_battery, percent, "Windows", f"ACLineStatus={ac_status}")


def _linux_power_snapshot() -> PowerSnapshot:
    root = Path("/sys/class/power_supply")
    if not root.exists():
        return PowerSnapshot(False, platform="Linux", details="/sys/class/power_supply is unavailable.")

    batteries = [p for p in root.iterdir() if p.name.upper().startswith("BAT")]
    online_values: list[int] = []
    for supply in root.iterdir():
        online_path = supply / "online"
        if supply in batteries or not online_path.exists():
            continue
        try:
            online_values.append(int(online_path.read_text().strip()))
        except Exception:  # noqa: BLE001
            continue

    percents: list[int] = []
    for battery in batteries:
        capacity_path = battery / "capacity"
        try:
            percents.append(int(capacity_path.read_text().strip()))
        except Exception:  # noqa: BLE001
            continue

    percent = round(sum(percents) / len(percents)) if percents else None
    has_ac_online = any(value == 1 for value in online_values)
    if batteries:
        on_battery = not has_ac_online
        source = "battery" if on_battery else "ac"
    else:
        on_battery = False if has_ac_online else None
        source = "ac" if has_ac_online else "unknown"

    return PowerSnapshot(
        True,
        source,
        on_battery,
        percent,
        "Linux",
        f"batteries={len(batteries)} online_supplies={len(online_values)}",
    )
