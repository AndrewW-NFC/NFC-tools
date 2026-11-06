# BirdNET 3 integration validation — November 6, 2026

Validated on the maintainer's Apple Silicon Mac. This is software compatibility
validation, not an accuracy benchmark for nocturnal flight calls.

- Full Python suite: 1,120 passed, 3 skipped.
- After adding explicit UI error-state handling for refused legacy recovery:
  61 relevant tests passed, including the added legacy-recovery regression.
- JavaScript: 41 passed; syntax checks passed for all browser scripts.
- Ruff reference/unused-import checks, release-version consistency, dependency
  name consistency, and wheel build passed.
- Dashboard, Settings, Schedule, and Import Recordings returned HTTP 200 in the
  production profile. Configuration bytes match the pre-upgrade backup.
- Scheduling and recording lifecycle tests passed with simulated devices/events.
  The user's automatic OS schedule was disabled and remains disabled.
- Installed the pinned Analyzer into a fresh production `birdnet3` environment;
  verified package provenance and `birdnet==1.4.0`. First inference downloaded
  fresh acoustic and geographic models into the production model cache.
- Confirmed the previous app still finds the intact BirdNET Analyzer 2.4.0 install.

## Real-audio checks

All runs used copies of their sources and separate output folders.

| Input | Settings | Outcome | Elapsed |
| --- | --- | --- | --- |
| Repository mute-swan wings fixture | Seasonal week 41, confidence 0.5 | Success; no retained detections | 136.88 s, including first model downloads |
| Repository mute-swan background fixture | Year-round, confidence 0.5 | Success; no retained detections | 1.92 s |
| Official preview `example/soundscape.wav` | Year-round, confidence 0.1, both sensitivity groups enabled | Success; one review clip | 3.59 s |

Test location was latitude 50, longitude 10. The positive sample demonstrates
result parsing and clip export; it is not a verified identification. The eBird
result reader successfully read the positive output. No checklist was uploaded.
Each run resumed without rewriting completed analysis. A separate process also
resumed a completed run without rewriting its model-policy file.

Local evidence: `~/Desktop/nfc-tools-upgrade-check-2026-11-06/validation.json`,
with the copied audio, CSVs, policy files, review files, and clip under that folder.

## Remaining field validation

A full overnight run with the intended microphone, representative manually
reviewed nocturnal recordings, confidence calibration, long-running imports,
and fresh Windows/Linux installations have not been tested in this integration.
The existing development checkout remains available for further comparisons.
