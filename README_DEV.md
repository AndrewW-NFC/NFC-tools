# NFC Tools — Developer notes

## Install from source

	git clone <repo> nfc-tools
	cd nfc-tools
	python -m venv .venv && source .venv/bin/activate
	pip install -e ".[dev]"
	nfc doctor

## CLI

	nfc doctor                # health checks
	nfc devices               # list audio inputs
	nfc install-analyzers     # install BirdNET + Nighthawk
	nfc record                # start a session using saved settings
	nfc record-once           # one session, synchronous (used by autoschedule)
	nfc analyze /path/to.wav  # re-analyze a single file
	nfc backfill 2026-05-10   # re-analyze a whole night
	nfc export 2026-05-10 --ebird --min-conf 0.7 --out tonight.csv
	nfc autoschedule --enable
	nfc autoschedule --disable
	nfc web                   # launch the local web app

## Running the web app in dev

	uvicorn nfc_tools.web.server:create_app --reload --factory

## Adding a custom analyzer

Create a Python module that registers a plugin via
nfc_tools.analyzers.base.register(...). Drop it into your data dir
under analyzers/myplugin.py and add "myplugin" to analyzers.enabled
in config.yaml.

## Where things are

- config.py — pydantic schema + YAML persistence.
- paths.py — cross-platform user dirs.
- recorder.py — ffmpeg segment-mode wrapper.
- session.py — orchestrator: schedule -> recorder -> analyzers.
- installer.py — pip + micromamba bootstrap for analyzers.
- analyzers/ — built-in plugins (BirdNET, Nighthawk).
- detections.py — parses analyzer outputs into a uniform record.
- exporters.py — CSV and eBird-format export.
- ephemeris.py — sunset/sunrise math (no heavy deps).
- autoschedule.py — cross-platform user-level schedulers.
- web/ — FastAPI routes, templates, static assets.

## Building a desktop bundle

	pip install briefcase
	briefcase create
	briefcase build
	briefcase package

## Testing

	pytest -q

## Generating documentation screenshots

	pip install playwright jinja2
	playwright install chromium
	python tools/make_screenshots.py            # HTML mockups
	python tools/make_screenshots.py --png      # also PNGs

## Architecture decisions

- Recording engine: ffmpeg (not SoX). More reliable on modern macOS
  Core Audio; cross-platform; widely packaged.
- Web UI instead of native: works identically on macOS, Windows, and
  Linux; no Accessibility or UIAutomation gymnastics.
- Managed venvs for analyzers: isolation, easy repair.
- Plugin protocol so the project can grow beyond BirdNET/Nighthawk.
