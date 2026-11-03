# BirdNET 3.0 development preview

This branch adds an isolated NFC Tools development profile. It is a first trial,
not a claim that BirdNET 3.0 identifies nocturnal flight calls more accurately.

## Run it

Launch `nfc-tools-dev`. It opens http://127.0.0.1:8766 and displays an experimental
banner. The regular `nfc-tools` launcher uses its existing profile on port 8765.
Keep the terminal open; Ctrl+C stops the development app.

On the maintainer's Mac, the development checkout lives at `~/Desktop/nfc-tools-dev`.
Its `.venv` contains the development app; a link in the existing command directory
makes `nfc-tools-dev` available from any terminal folder.

To reproduce on another machine, check out `codex/birdnet-3-support`, create a
virtual environment, install with `python -m pip install -e '.[dev]'`, then run
that environment's `nfc-tools-dev` command. Install BirdNET through Settings.
The first analysis downloads the acoustic and geographic models.

## First trial

1. Open Settings and check the recording location and confidence settings.
   Development settings start fresh; production settings are not copied.
2. Open Import Recordings. BirdNET is selected; Nighthawk and wingbeats are off.
3. Select a small set of existing recordings. Originals are read, not edited.
4. Keep output under `~/Desktop/nfc-tools-dev-output`. This is enforced for
   recording, import preparation, scanning, and checkpoint recovery.
5. Review the dates, recording location, timeline, storage estimate, and results.

Use separate output subfolders for separate comparisons. Keep the same original
recordings for the regular 2.4 run and the development 3.0 run. Compare confirmed
calls, missed calls, false positives, review time, and analysis time. Scores are
not calibrated between models. Neither model is ground truth.

## Isolation and implementation

- Config, data, logs, analyzer environments, and app caches use `nfc-tools-dev`
  platform directories. BirdNET model downloads use the development data folder.
- Automatic OS scheduling is disabled in this first preview, including enable
  and disable requests, so it cannot change the regular app's scheduled task.
- The original profile still uses Analyzer 2.4.0. The development profile pins
  Analyzer commit `032dcaca6afb2a3438965f80d5e01de0fb2036b4` and `birdnet==1.4.0`,
  selecting acoustic model 3.0 (preview 3.1) explicitly.
- Uses per-recording tables, omits the week for year-round filtering, and uses
  the new species-list API for the finch/owl overrides.
- One inference worker limits initial resource use; larger batches need timing
  and memory benchmarks before tuning this.
- Result policy JSON records the model, preview, library pin, Analyzer source,
  location, week, and sensitivity settings.
- Both CSV and Raven output use the same review threshold policy. Parameter CSVs
  are excluded from detection filtering. Unknown eBird codes fall back to readable
  common names in clip filenames.

## Remaining evaluation

A successful installation and short inference test do not establish flight-call
accuracy. Representative nights, threshold selection, long-running imports,
pause/resume under real workloads, and fresh Windows/Linux installs need further
validation. Updated common names and missing eBird codes need review before
uploading checklists. Automatic recording and switching model versions within
one profile are intentionally outside this first trial.

Upstream references:
- https://birdnet-team.github.io/BirdNET-Analyzer/dev/breaking-changes.html
- https://github.com/birdnet-team/birdnet-V3.0-dev

## Validation of this first draft (2026-11-03)

- Full Python suite: 1,077 passed, 3 skipped before the final installer pin check
  was added; the changed installer and adapter paths then passed their focused tests.
- JavaScript suite: 41 passed. Version/dependency consistency and Ruff checks passed.
- Installed the pinned Analyzer in a fresh private Python 3.11 environment on
  Apple Silicon macOS. Confirmed Analyzer 3.0.0, birdnet 1.4.0, ONNX Runtime 1.31.1.
- Real inference on the repository's wingbeat fixture with both sensitivity
  overrides enabled succeeded with zero retained detections.
- Real inference on the official preview repository's `example/soundscape.wav`
  succeeded using year-round filtering, latitude 50/longitude 10, threshold 0.1,
  and the isolated model cache. Produced one Red Crossbill candidate (0.5011)
  from 27–30 seconds and exported one review clip. This tests the pipeline;
  it is not a verified identification or a flight-call accuracy benchmark.
- Browser check confirmed the banner, BirdNET-only import default, and prefilled
  development output folder. Both launch commands resolve to separate checkouts.
