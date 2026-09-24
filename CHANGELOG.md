# Changelog

## Unreleased

- Remove slow loudness trends from WING broadband repetition and cross-band
  synchrony checks to reduce wind-related false positives.

- Make WING evaluation CSV intervals readable, show "None detected" for empty
  results, and write UTF-8 with a BOM for spreadsheet compatibility. The evaluation
  script now also accepts individual WAV/MP3 files.

- Keep WING surrounding-noise measurement regions fixed within each window to
  reduce false positives caused by shifting spectral peaks in uneven background noise.

- Extend experimental WING screening to repeating tones with synchronized
  surrounding noise, with leakage guards and analysis up to 10 kHz.

- Add Night Summary with scheduled coverage, recording gaps, invalid/missing audio,
  per-analyzer progress, export status, and recovery after app restarts.
- Persist inference and clip-export checkpoints; retry unfinished work without
  repeating completed inference or creating duplicate numbered clips.
- Flag silent and very quiet Readiness Check samples while preserving playback.


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
