# Changelog

## 0.6.0 — Phase C
- Removed the first-run wizard and Recording Checklist tab; setup now happens through Settings and Readiness Check.
- Removed in-app detection review, clip playback, and detection export surfaces.
- Review clips are exported from analyzer result files after successful analysis.
- Cross-platform auto-scheduling (launchd / systemd --user / Task Scheduler).
- Sun-altitude twilight schedule presets via NOAA-style solar math.
- Astronomical preset records civil dusk to civil dawn and labels civil-to-astronomical twilight files separately.
- Removed stale synthetic screenshot generator and SVG mockups from documentation.

## 0.5.0 — Phases A + B
- Python package replacing the zsh + AppleScript pipeline.
- ffmpeg-based recorder (cross-platform).
- Local web app: first-run wizard, dashboard, settings, and diagnostics.
- Auto-installer for ffmpeg, BirdNET, Nighthawk.
- Plugin protocol for analyzers.
- CLI: doctor, devices, install-analyzers, record, analyze, backfill, web.
- New filename format (legacy still parsed).
