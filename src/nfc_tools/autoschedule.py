"""Cross-platform 'record every night automatically' setup.

The user clicks Enable in the Schedule page; we install a launcher
that runs `nfc record-once` at the configured start time. The
record-once command exits when the session ends, so the OS scheduler
can re-launch it the next night cleanly.
"""
from __future__ import annotations
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .logging_setup import get
from .paths import data_dir

log = get("autoschedule")

LABEL = "org.nfctools.recorder"


@dataclass
class ScheduleStatus:
	enabled: bool
	backend: str            # "launchd" | "systemd" | "schtasks" | "unsupported"
	detail: str = ""
	next_run_hint: str = ""


def _python_executable() -> str:
	nfc = shutil.which("nfc")
	return nfc or sys.executable


def _start_command(start_time: str) -> list[str]:
	nfc = _python_executable()
	if Path(nfc).name == "nfc":
		return [nfc, "record-once"]
	return [nfc, "-m", "nfc_tools", "record-once"]


# ----------------- macOS / launchd -----------------

def _launchd_plist_path() -> Path:
	return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _launchd_install(start_time: str) -> ScheduleStatus:
	hh, mm = (int(x) for x in start_time.split(":"))
	cmd = _start_command(start_time)
	args = "".join(f"<string>{c}</string>" for c in cmd)
	plist = (
		'<?xml version="1.0" encoding="UTF-8"?>\n'
		'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
		'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
		'<plist version="1.0"><dict>\n'
		f'  <key>Label</key><string>{LABEL}</string>\n'
		'  <key>ProgramArguments</key>\n'
		f'  <array>{args}</array>\n'
		'  <key>StartCalendarInterval</key>\n'
		f'  <dict><key>Hour</key><integer>{hh}</integer>'
		f'<key>Minute</key><integer>{mm}</integer></dict>\n'
		f'  <key>StandardOutPath</key><string>{data_dir() / "autoschedule.out.log"}</string>\n'
		f'  <key>StandardErrorPath</key><string>{data_dir() / "autoschedule.err.log"}</string>\n'
		'  <key>RunAtLoad</key><false/>\n'
		'</dict></plist>\n'
	)
	p = _launchd_plist_path()
	p.parent.mkdir(parents=True, exist_ok=True)
	p.write_text(plist)
	subprocess.run(["launchctl", "unload", str(p)], check=False, capture_output=True)
	subprocess.run(["launchctl", "load", str(p)], check=True)
	return ScheduleStatus(True, "launchd",
						  f"LaunchAgent installed at {p}",
						  f"Daily at {start_time}")


def _launchd_uninstall() -> ScheduleStatus:
	p = _launchd_plist_path()
	if p.exists():
		subprocess.run(["launchctl", "unload", str(p)], check=False, capture_output=True)
		p.unlink()
	return ScheduleStatus(False, "launchd", "Removed.", "")


def _launchd_status() -> ScheduleStatus:
	p = _launchd_plist_path()
	return ScheduleStatus(p.exists(), "launchd",
						  f"plist {'present' if p.exists() else 'not present'}: {p}")


# ----------------- Linux / systemd --user -----------------

def _systemd_user_dir() -> Path:
	return Path.home() / ".config" / "systemd" / "user"


def _systemd_install(start_time: str) -> ScheduleStatus:
	cmd = _start_command(start_time)
	exec_start = " ".join(cmd)
	unit_dir = _systemd_user_dir()
	unit_dir.mkdir(parents=True, exist_ok=True)
	service = unit_dir / f"{LABEL}.service"
	timer = unit_dir / f"{LABEL}.timer"
	service.write_text(
		"[Unit]\n"
		"Description=NFC Tools nightly recording\n"
		"[Service]\n"
		"Type=simple\n"
		f"ExecStart={exec_start}\n"
	)
	timer.write_text(
		"[Unit]\n"
		f"Description=Run NFC Tools nightly at {start_time}\n"
		"[Timer]\n"
		f"OnCalendar=*-*-* {start_time}:00\n"
		"Persistent=true\n"
		"[Install]\n"
		"WantedBy=timers.target\n"
	)
	subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
	subprocess.run(["systemctl", "--user", "enable", "--now", f"{LABEL}.timer"], check=True)
	return ScheduleStatus(True, "systemd",
						  f"User timer installed in {unit_dir}",
						  f"Daily at {start_time}")


def _systemd_uninstall() -> ScheduleStatus:
	subprocess.run(["systemctl", "--user", "disable", "--now", f"{LABEL}.timer"],
				   check=False, capture_output=True)
	for name in (f"{LABEL}.service", f"{LABEL}.timer"):
		p = _systemd_user_dir() / name
		if p.exists(): p.unlink()
	subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True)
	return ScheduleStatus(False, "systemd", "Removed.", "")


def _systemd_status() -> ScheduleStatus:
	p = _systemd_user_dir() / f"{LABEL}.timer"
	if not p.exists():
		return ScheduleStatus(False, "systemd", "Not installed.")
	r = subprocess.run(["systemctl", "--user", "is-active", f"{LABEL}.timer"],
					   capture_output=True, text=True)
	return ScheduleStatus(r.stdout.strip() == "active", "systemd",
						  r.stdout.strip() or "unknown")


# ----------------- Windows / schtasks -----------------

def _schtasks_install(start_time: str) -> ScheduleStatus:
	cmd = _start_command(start_time)
	quoted = " ".join(f'"{c}"' for c in cmd)
	subprocess.run(
		["schtasks", "/Create", "/F", "/SC", "DAILY",
		 "/TN", LABEL, "/ST", start_time, "/TR", quoted],
		check=True, capture_output=True,
	)
	return ScheduleStatus(True, "schtasks", "Scheduled task created.",
						  f"Daily at {start_time}")


def _schtasks_uninstall() -> ScheduleStatus:
	subprocess.run(["schtasks", "/Delete", "/F", "/TN", LABEL],
				   check=False, capture_output=True)
	return ScheduleStatus(False, "schtasks", "Removed.", "")


def _schtasks_status() -> ScheduleStatus:
	r = subprocess.run(["schtasks", "/Query", "/TN", LABEL],
					   capture_output=True, text=True)
	return ScheduleStatus(r.returncode == 0, "schtasks",
						  (r.stdout or r.stderr).strip())


# ----------------- Public API -----------------

def _backend() -> str:
	s = platform.system()
	if s == "Darwin":  return "launchd"
	if s == "Linux":   return "systemd"
	if s == "Windows": return "schtasks"
	return "unsupported"


def install(start_time: str) -> ScheduleStatus:
	b = _backend()
	if b == "launchd":  return _launchd_install(start_time)
	if b == "systemd":  return _systemd_install(start_time)
	if b == "schtasks": return _schtasks_install(start_time)
	return ScheduleStatus(False, "unsupported", "OS not supported.")


def uninstall() -> ScheduleStatus:
	b = _backend()
	if b == "launchd":  return _launchd_uninstall()
	if b == "systemd":  return _systemd_uninstall()
	if b == "schtasks": return _schtasks_uninstall()
	return ScheduleStatus(False, "unsupported", "OS not supported.")


def status() -> ScheduleStatus:
	b = _backend()
	if b == "launchd":  return _launchd_status()
	if b == "systemd":  return _systemd_status()
	if b == "schtasks": return _schtasks_status()
	return ScheduleStatus(False, "unsupported", "OS not supported.")
