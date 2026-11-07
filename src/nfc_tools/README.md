# NFC Tools application

This package owns nocturnal recording, imported-audio analysis, saved-night recovery, and exports.

The main flow is `app` / `cli` → `web` or `session` → recorder backends → `analyzers` → clips, manifests, and eBird exports. `importer` feeds existing audio into the same archive conventions. `review` is a separate human-listening workspace.

Python dependency versions live in [pyproject.toml](../../pyproject.toml). External runtimes such as ffmpeg, BirdNET, and Nighthawk are located or installed by `ffmpeg_locator` and `installer`. File headers explain the important relationships without repeating every import.

## Files

| File | Purpose |
| --- | --- |
| [__init__.py](__init__.py) | NFC Tools — record and analyze nocturnal flight calls. |
| [__main__.py](__main__.py) | Allow `python -m nfc_tools` to run the CLI. |
| [acoustics.py](acoustics.py) | Weather-only adaptation of NFC acoustic environment forecast v2.2.12. |
| [app.py](app.py) | Entry point for the GUI launcher: starts the web app and opens a browser. |
| [autoschedule.py](autoschedule.py) | Cross-platform 'record every night automatically' setup. |
| [birdnet_policy.py](birdnet_policy.py) | Shared eligibility and confidence rules for BirdNET review candidates. |
| [birdnet_version.py](birdnet_version.py) | Prevent upgrades from mixing analyzer versions in an existing analysis. |
| [buzz.py](buzz.py) | Experimental screening for the persistent broad buzz in field examples. |
| [cli.py](cli.py) | Command-line interface for tinkerers and headless setups. |
| [clip_exporter.py](clip_exporter.py) | Export short review clips from analyzer result labels. |
| [clip_metadata.py](clip_metadata.py) | Portable clip provenance. Never include review information, in any schema version. |
| [closed_lid.py](closed_lid.py) | Temporary macOS lid-sleep override, guarded by an independent root watchdog. |
| [config.py](config.py) | User-facing configuration, persisted as YAML. |
| [dev.py](dev.py) | Dedicated development launcher; choose the profile before importing the app. |
| [devices.py](devices.py) | Audio input device enumeration via ffmpeg. |
| [doctor.py](doctor.py) | Health checks. Plain-English errors, fixable suggestions. |
| [ebird_export.py](ebird_export.py) | Prepare eBird spreadsheet-import CSVs from NFC Tools analysis results. |
| [ebird_locations.py](ebird_locations.py) | Optional public hotspot lookup. Personal locations require the user's eBird account. |
| [ebird_rarity.py](ebird_rarity.py) | Local reviewer filters. Dates are annual, inclusive change points. |
| [ephemeris.py](ephemeris.py) | Sun and twilight computation using NOAA's algorithm. |
| [ffmpeg_locator.py](ffmpeg_locator.py) | Locate or auto-install ffmpeg. |
| [filenames.py](filenames.py) | Filename parsing. One source of truth for the recording naming convention. |
| [folder_picker.py](folder_picker.py) | Open native local folder and recording file pickers. |
| [import_sources.py](import_sources.py) | Resolve explicit files and recursive folders into one import selection. |
| [importer.py](importer.py) | Checkpointed, read-only source import into the normal nightly archive. |
| [installer.py](installer.py) | Installs ffmpeg, BirdNET-Analyzer, and Nighthawk into managed venvs. |
| [lock.py](lock.py) | Cross-platform serialization of analysis jobs via atomic mkdir. |
| [logging_setup.py](logging_setup.py) | Structured application logging and rotating log files. |
| [manifest.py](manifest.py) | Per-night CSV manifest for downstream tools and support diagnostics. |
| [night_status.py](night_status.py) | Durable analysis checkpoints and recording coverage, independent of app uptime. |
| [notifications.py](notifications.py) | Cross-platform desktop notifications. Falls back to logging. |
| [paths.py](paths.py) | Cross-platform paths for config, data, logs, and cache. |
| [power.py](power.py) | Cross-platform power source and sleep-prevention helpers. |
| [precipitation.py](precipitation.py) | Comparable overnight model estimates; never total recording-start snapshots. |
| [readiness.py](readiness.py) | Automated night-readiness checks for the local web UI. |
| [recorder.py](recorder.py) | ffmpeg-based segment recorder. |
| [schedule_resolver.py](schedule_resolver.py) | Resolve fixed or twilight-based recording schedules. |
| [scheduler.py](scheduler.py) | Compute session timing windows. Pure functions; easy to test. |
| [segments.py](segments.py) | Helpers for NFC-window segment naming and split points. |
| [session.py](session.py) | Coordinates a recording session: schedule, recorder, per-segment analysis. |
| [session_logging.py](session_logging.py) | CSV-backed session log helpers for the local dashboard. |
| [sounddevice_common.py](sounddevice_common.py) | Shared sounddevice/CoreAudio helpers for recording and diagnostics. |
| [sounddevice_diagnostics.py](sounddevice_diagnostics.py) | Sounddevice / PortAudio recording diagnostics. |
| [sounddevice_recorder.py](sounddevice_recorder.py) | sounddevice / PortAudio / CoreAudio recording backend. |
| [version.py](version.py) | Single source of truth for the package version. |
| [weather.py](weather.py) | Weather snapshot from Open-Meteo. Retried requests with a bounded forecast fallback. |

## Subfolders

- [analyzers](analyzers/README.md): detector adapters and wingbeat screening.
- [web](web/README.md): recorder HTTP routes and browser interface.
- [review](review/README.md): independent human-listening workspace.
- [data](data/README.md): packaged taxonomy and notification audio.
