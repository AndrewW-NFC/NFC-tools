# Changelog

## 0.6.0 — Phase C
- Recording Checklist memory aid as its own navigation tab.
- Removed in-app detection review, clip playback, and detection export surfaces.
- Cross-platform auto-scheduling (launchd / systemd --user / Task Scheduler).
- Sun-altitude twilight schedule presets via NOAA-style solar math.
- Astronomical preset records civil dusk to civil dawn and labels civil-to-astronomical twilight files separately.
- Synthetic screenshot generator and SVG mockups for documentation.

## 0.5.0 — Phases A + B
- Python package replacing the zsh + AppleScript pipeline.
- ffmpeg-based recorder (cross-platform).
- Local web app: first-run wizard, dashboard, settings, and diagnostics.
- Auto-installer for ffmpeg, BirdNET, Nighthawk.
- Plugin protocol for analyzers.
- CLI: doctor, devices, install-analyzers, record, analyze, backfill, web.
- New filename format (legacy still parsed).
