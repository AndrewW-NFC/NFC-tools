"""Command-line interface for tinkerers and headless setups."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from . import config as config_mod
from . import doctor as doctor_mod
from . import installer
from .devices import list_input_devices
from .logging_setup import setup as setup_logging
from .session import Session, analyze_existing

console = Console()


@click.group()
@click.version_option()
def main():
	"""NFC Tools — record and analyze nocturnal flight calls."""
	setup_logging()


@main.command()
def doctor():
	"""Run health checks."""
	checks = doctor_mod.run_all()
	table = Table(title="NFC Tools — Health Check")
	table.add_column("Check"); table.add_column("OK"); table.add_column("Detail"); table.add_column("Fix")
	for c in checks:
		table.add_row(c.name, "OK" if c.ok else "FAIL", c.detail, c.fix_hint)
	console.print(table)
	raise SystemExit(0 if all(c.ok for c in checks) else 2)


@main.command()
def devices():
	"""List audio input devices."""
	for d in list_input_devices():
		console.print(f"[bold]{d['id']}[/]  {d['name']}")


@main.command(name="install-analyzers")
@click.option("--only", multiple=True, type=click.Choice(["birdnet", "nighthawk"]))
def install_analyzers(only):
	"""Install BirdNET and/or Nighthawk into managed environments."""
	targets = list(only) if only else ["birdnet", "nighthawk"]

	def cb(msg, frac):
		console.print(f"  {msg}")

	for t in targets:
		if t == "birdnet":
			installer.install_birdnet(cb)
		elif t == "nighthawk":
			installer.install_nighthawk(cb)


@main.command()
def record():
	"""Start a recording session right now using saved settings.

	Runs until the configured end time or until you press Ctrl-C.
	"""
	cfg = config_mod.load()
	if not cfg.recording.device:
		console.print("[red]No microphone configured.[/] Run [bold]nfc devices[/] then "
					  "edit your config, or use the web UI.")
		raise SystemExit(1)

	async def run():
		sess = Session(cfg)
		await sess.start()
		console.print("[green]Recording. Press Ctrl-C to stop.[/]")
		try:
			while sess.status["state"] != "idle":
				await asyncio.sleep(2)
		except KeyboardInterrupt:
			await sess.stop("user")

	asyncio.run(run())


@main.command(name="record-once")
def record_once():
	"""Run a single session synchronously and exit. Used by autoschedule."""
	cfg = config_mod.load()
	if cfg.schedule.auto_apply_preset and cfg.schedule.preset:
		from .ephemeris import preset_times
		s, e = preset_times(cfg.schedule.preset, cfg.site.latitude,
							cfg.site.longitude, cfg.site.timezone)
		cfg.schedule.start_time, cfg.schedule.end_time = s, e
		config_mod.save(cfg)

	async def run():
		sess = Session(cfg)
		await sess.start()
		while sess.status["state"] != "idle":
			await asyncio.sleep(5)

	asyncio.run(run())


@main.command()
@click.argument("wav", type=click.Path(exists=True, dir_okay=False, path_type=Path))
def analyze(wav: Path):
	"""Analyze a single existing WAV."""
	cfg = config_mod.load()
	res = analyze_existing(wav, cfg)
	console.print(json.dumps(res, indent=2))


@main.command()
def web():
	"""Launch the local web app."""
	from .web.server import run as run_web
	run_web()


@main.command()
@click.argument("session_date")
def backfill(session_date: str):
	"""Reanalyze all WAVs for a given session date."""
	from .paths import night_dir
	cfg = config_mod.load()
	nd = night_dir(session_date)
	audio = nd / "audio"
	if not audio.exists():
		console.print(f"[red]No audio dir at {audio}[/]")
		raise SystemExit(3)
	for wav in sorted(audio.glob("*.wav")):
		console.print(f"Analyzing {wav.name}...")
		analyze_existing(wav, cfg)


@main.command(name="export")
@click.argument("session_date")
@click.option("--ebird/--rich", default=False,
			  help="Export eBird-import format (default: rich CSV).")
@click.option("--min-conf", default=0.5, type=float)
@click.option("--out", type=click.Path(path_type=Path), default=None)
def export_cmd(session_date: str, ebird: bool, min_conf: float, out: Optional[Path]):
	"""Export detections for a night to CSV."""
	from .detections import collect_for_night
	from .exporters import to_rich_csv, to_ebird_csv
	cfg = config_mod.load()
	rows = collect_for_night(session_date, min_confidence=min_conf)
	body = to_ebird_csv(rows, cfg, min_confidence=min_conf) if ebird else to_rich_csv(rows)
	if out:
		out.write_text(body)
		console.print(f"Wrote {out}")
	else:
		console.print(body)


@main.command(name="autoschedule")
@click.option("--enable/--disable", default=True)
def autoschedule_cmd(enable: bool):
	"""Install or remove the nightly auto-recorder."""
	from . import autoschedule as a
	cfg = config_mod.load()
	s = a.install(cfg.schedule.start_time) if enable else a.uninstall()
	console.print(f"{s.backend}: {'enabled' if s.enabled else 'disabled'} - {s.detail}")


if __name__ == "__main__":
	main()
