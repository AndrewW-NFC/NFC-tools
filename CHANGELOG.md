# Changelog

## 0.7.0 — 2026-09-25

- Add experimental wingbeat screening to live and imported recordings, enabled by
  default for new configurations and imports. WING candidates produce review clips
  and CSV rows, without species assignments, confidence probabilities, or eBird counts.
- Improve WING pulse counting, wind detrending, and synchronized surrounding-noise
  checks to reduce false positives; extend screening to repeating tones up to 10 kHz.
- Add WING research instrumentation, source datasets, regression tests, and an audit.
  Improve evaluation CSV readability and support individual WAV/MP3 inputs.
  Field accuracy remains unestablished.
- Add Night Summary with scheduled coverage, recording gaps, missing or unreadable
  audio, analyzer progress, export status, and recovery after app restarts.
- Persist inference and clip-export checkpoints so recovery retries unfinished work
  without repeating completed inference or creating duplicate numbered clips.
- Write night and segment status snapshots, including completed analysis with no detections.
- Add bulk recording import with timeline review, recorder clock correction, audio
  conversion, analyzer selection, progress reporting, and pause/resume checkpoints.
  Preserve corrections when fixing output folders and prevent stale recovery from
  replacing a new import timeline.
- Add per-session and combined nightly eBird Record Format exports, full Nighthawk
  taxonomy mappings, and companion review CSVs. Use common names and BOM-free UTF-8
  in upload files; retain a BOM in review CSVs for spreadsheet compatibility.
- Separate recording locations from optional eBird exports, enabled by default.
  Support personal-location guidance and public-hotspot lookup with locally saved
  API keys, a forget-key control, and exclusion of saved keys from diagnostics.
- Add historical environmental conditions for imports, retry transient weather
  failures, refine checklist weather comments, and add comparable overnight
  precipitation reports with coverage and source metadata.
- Raise the default BirdNET confidence threshold to 0.500 and clarify the option
  to include species expected at the location at any time of year.
- Flag silent or very quiet readiness samples, recover stale analysis locks,
  handle invalid Windows lock PIDs, and strengthen macOS sleep prevention.
- Report built-in WING availability consistently, remove retired code, and expand
  CI checks across Ubuntu, Windows, and macOS on Python 3.10–3.12, including wheel
  installation, command entry points, web assets, Python checks, and browser tests.
- Introduce wingbeat screening in the README, shorten its experimental-feature
  notes, put Nighthawk before BirdNET in documentation, and remove the final
  standalone precipitation section. Refresh user and developer setup guidance.

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
- Auto-installer for ffmpeg, Nighthawk, BirdNET.
- Plugin protocol for analyzers.
- CLI: doctor, devices, install-analyzers, record, analyze, backfill, web.
- New filename format (legacy still parsed).
