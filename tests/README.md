# Regression tests

Tests protect recording lifecycle, analyzer contracts, import/recovery, exports, scheduling, weather, and web behavior. Most `test_*.py` names mirror the module or feature under test. Wingbeat tests combine synthetic signals with stored feature fixtures; they do not establish field accuracy.

From the repository root, run `python -m pytest -q` after installing `.[dev]`. Run browser-controller tests with `node --test tests/*.cjs`; they use Node built-ins and mocked DOM/network objects. Some Python tests exercise ffmpeg or platform-specific paths and may skip when prerequisites are unavailable.

[fixtures](fixtures/README.md) contains measured regression features and provenance. `precipitation-fixtures.json` supplies the shared overnight-precipitation contract cases. File headers identify the tested purpose and project/external imports; test fixtures and monkeypatches supply isolated state.

## Files

| File | Purpose |
| --- | --- |
| [test_acoustics.py](test_acoustics.py) | Regression tests for acoustics. |
| [test_autoschedule.py](test_autoschedule.py) | Regression tests for autoschedule. |
| [test_birdnet3.py](test_birdnet3.py) | Regression tests for BirdNET 3 output tables, policy, and provenance. |
| [test_birdnet_dates.py](test_birdnet_dates.py) | Regression tests for BirdNET recording-date and seasonal arguments. |
| [test_birdnet_sensitivity.py](test_birdnet_sensitivity.py) | Regression tests for BirdNET sensitivity arguments and configuration. |
| [test_birdnet_upgrade.py](test_birdnet_upgrade.py) | Regression tests for BirdNET upgrade identity and mixed-version safeguards. |
| [test_buzz.py](test_buzz.py) | Behavioral controls for experimental, persistent-only buzz screening. |
| [test_clip_exporter.py](test_clip_exporter.py) | Regression tests for review clip selection, audio boundaries, and embedded provenance. |
| [test_closed_lid.py](test_closed_lid.py) | Regression tests for guarded macOS lid-sleep leases and watchdog restoration. |
| [test_config.py](test_config.py) | Regression tests for configuration defaults, validation, migration, and persistence. |
| [test_dev_profile.py](test_dev_profile.py) | Check isolation in fresh processes, before import-time path constants exist. |
| [test_devices.py](test_devices.py) | Regression tests for devices. |
| [test_ebird_export.py](test_ebird_export.py) | Regression tests for eBird CSV formatting, taxonomy mapping, and recording context. |
| [test_ebird_locations.py](test_ebird_locations.py) | Regression tests for hotspot selection, API-key persistence, and diagnostic redaction. |
| [test_ebird_rarity.py](test_ebird_rarity.py) | Regression tests for reviewer-filter parsing, site association, and export annotations. |
| [test_ephemeris.py](test_ephemeris.py) | Regression tests for ephemeris. |
| [test_file_picker.py](test_file_picker.py) | Regression tests for native multi-file selection and folder-picker defaults. |
| [test_filenames.py](test_filenames.py) | Regression tests for filenames. |
| [test_importer.py](test_importer.py) | Regression tests for import planning, conversion, checkpoints, and recovery. |
| [test_installer.py](test_installer.py) | Regression tests for isolated analyzer installation, version checks, and retry behavior. |
| [test_lock_process.py](test_lock_process.py) | Real-process regression tests for lock-owner liveness checks. |
| [test_macaulay_collect.py](test_macaulay_collect.py) | Offline contract tests: no requests to Cornell or downloads of real recordings. |
| [test_night_status.py](test_night_status.py) | Regression tests for night coverage, saved progress, and resumable analysis. |
| [test_notifications.py](test_notifications.py) | Regression tests for bundled completion audio and nonfatal playback failure. |
| [test_power.py](test_power.py) | Regression tests for power. |
| [test_precipitation.py](test_precipitation.py) | Regression tests for overnight precipitation totals, saved context, and refresh endpoints. |
| [test_readiness.py](test_readiness.py) | Regression tests for pre-recording checks, grouped status, and audio-level assessment. |
| [test_recording_lifecycle.py](test_recording_lifecycle.py) | Regression tests for capture startup, segment boundaries, lock ownership, and session cleanup. |
| [test_recording_review.py](test_recording_review.py) | Regression tests for review validation, revisions, backups, and audio request boundaries. |
| [test_schedule_resolver.py](test_schedule_resolver.py) | Regression tests for schedule resolver. |
| [test_scheduler.py](test_scheduler.py) | Regression tests for scheduler. |
| [test_segments.py](test_segments.py) | Regression tests for segments. |
| [test_weather.py](test_weather.py) | Regression tests for weather snapshots, retries, historical lookup, and forecast fallback. |
| [test_web_server.py](test_web_server.py) | Regression tests for web routes, session controls, settings, and rendered page contracts. |
| [test_wingbeat_accompaniment.py](test_wingbeat_accompaniment.py) | Regression tests for pulse-linked spectral support and interference rejection. |
| [test_wingbeat_brief.py](test_wingbeat_brief.py) | Brief accompaniment windows retain strict gates and streaming boundaries. |
| [test_wingbeat_call_motion.py](test_wingbeat_call_motion.py) | Swept-call rejection must preserve stable/no-bass and overlapping wing pulses. |
| [test_wingbeat_call_rejection.py](test_wingbeat_call_rejection.py) | Call-like controls for pulse-linked spectral support; no species classifier. |
| [test_wingbeat_frames.py](test_wingbeat_frames.py) | Caching must preserve every window's features and merged detections. |
| [test_wingbeat_localized_pulses.py](test_wingbeat_localized_pulses.py) | Localized upper-band pulses need neither a bass component nor a thin whistle. |
| [test_wingbeat_midband.py](test_wingbeat_midband.py) | A stronger neighboring sound must not hide a supported mid-band passage. |
| [test_wingbeat_refinement.py](test_wingbeat_refinement.py) | Regression tests for short-window recovery, rhythm gates, and stream boundaries. |
| [test_wingbeat_research.py](test_wingbeat_research.py) | Research sidecar contract: production sources stay untouched. |
| [test_wingbeat_spectral_support.py](test_wingbeat_spectral_support.py) | Noise bursts need bass support; a real wing whistle can be high-frequency. |
| [test_wingbeat_upper_interference.py](test_wingbeat_upper_interference.py) | Reject an insect-like companion lobe without a general high-frequency veto. |
| [test_wingbeat_waterfowl.py](test_wingbeat_waterfowl.py) | Measured regression windows and counterexamples for waterfowl recovery. |
| [test_wingbeats.py](test_wingbeats.py) | Regression tests for wingbeat screening, decoding, clip export, and review-only output. |
