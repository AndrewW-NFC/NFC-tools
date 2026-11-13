# NFC Tools — Developer notes

For file and folder responsibilities, see the [codebase guide](CODEBASE.md).

> See [BirdNET 3.0 integration and upgrade notes](docs/birdnet-3-upgrade.md). The isolated `nfc-tools-dev` profile remains available.

These notes are for people modifying NFC Tools itself. For end-user instructions, see [README.md](README.md). For the wingbeat detector overview, criteria, limitations, and recording credits, see [README_WINGBEATS.md](README_WINGBEATS.md).

macOS is the best-tested platform, with thousands of recordings. Linux has been
tested in an Ubuntu virtual machine, but not for overnight recording. Windows
passes automated tests and has one reported successful real-world use. These
reports do not establish that every microphone, scheduler, or packaged app works
on every platform. Changes to those integrations need hands-on checks as well as
automated tests.

## Quick setup

Clone the repository:

```bash
git clone https://github.com/AndrewW-NFC/NFC-tools.git
cd NFC-tools
```

Use Python 3.10 or newer. Create and activate a virtual environment.

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install in editable development mode:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the editable-install command again when updating an existing checkout. The
development dependencies include `httpx2>=2.0` and `starlette>=1.7.0` for the
current TestClient and AnyIO portal API. Application HTTP requests still use
`httpx`; the test dependencies do not change the desktop packaging requirements.

Run basic checks:

```bash
python -m compileall -q src/nfc_tools
python -m ruff check --isolated --select F src tests tools scripts
python -m pytest -q
python scripts/check_versions.py
git diff --check
```

On Python 3.11 or newer, also compare the runtime dependency names in the two
packaging manifests:

```bash
python scripts/check_dependencies.py
```

To check for dependency deprecations as well, run
`python -m pytest -q -W error::DeprecationWarning`. Test counts and results
change as the suite grows; use the current run or CI result.

`nfc doctor` additionally checks your actual microphone, network, and installed analyzers; it is a local setup check rather than an isolated test.

The test suite includes mocked Windows/Linux coverage for scheduling, sleep prevention,
ffmpeg backend selection, and device-enumeration parsing. `tests/test_lock_process.py`
also starts real child processes to check live-owner preservation and exited-owner
lock recovery on each CI operating system. Real microphone access,
systemd user timers, Windows Task Scheduler, and packaged-app launch still need
hands-on testing on those operating systems before release claims should be strengthened.

With Node.js installed, check all browser scripts and run all three browser test suites:

```bash
python -c "from pathlib import Path; import subprocess; [subprocess.run(['node', '--check', str(path)], check=True) for path in sorted(Path('src/nfc_tools/web/static').glob('*.js'))]"
node --test tests/test_import_timeline.cjs tests/test_ebird_location.cjs tests/test_live_progress.cjs
```

These commands work in a shell or PowerShell. Node.js is needed for browser-code
checks, but is not required to run NFC Tools. For changes to timeline handling,
also run the timeline suite with different `TZ` environment settings.

## Cross-platform checks

GitHub Actions runs the basic project checks on Ubuntu, Windows, and macOS for
every push and pull request, using Python 3.10, 3.11, and 3.12 (nine jobs). The workflow lives at `.github/workflows/ci.yml`.

The CI job installs NFC Tools in editable development mode, compiles the Python
package, runs Ruff’s `F` checks and the pytest suite, syntax-checks every browser
JavaScript file, and runs the import-timeline, eBird-location, and live-progress browser tests.
It also builds and installs a wheel, checks installed CLI entry points, and
verifies packaged web assets. These checks are intended to catch portable-code problems early, such as
path handling, case sensitivity, shell differences, and dependency issues.

CI also runs `scripts/check_versions.py` on every job and
`scripts/check_dependencies.py` on Python 3.11 and 3.12 (it uses `tomllib`). The
first checks `VERSION`, `pyproject.toml`, `briefcase.toml`, and
`src/nfc_tools/version.py` for agreement. The second compares normalized package
names, ignoring version constraints and extras; it does not build a Briefcase
desktop package.

CI does not replace real operating-system testing for microphone access,
systemd user timers, Windows Task Scheduler, packaged-app launch, or attached
audio/NFC hardware.

## Running the app in development

Launch the normal local browser app:

```bash
nfc-tools
```

Alternatively, launch the web app and browser through the CLI:

```bash
nfc web
```

Run the FastAPI app with reload:

```bash
uvicorn nfc_tools.web.server:create_app --reload --factory --host 127.0.0.1 --port 8765
```

The default local URL is:

```text
http://127.0.0.1:8765/
```

## Command-line interface

The `nfc` command is defined in `pyproject.toml` and implemented in `src/nfc_tools/cli.py`.

Current commands:

| Command | Implementation note |
| --- | --- |
| `nfc doctor` | Runs `doctor.run_all()` and exits nonzero if any check fails. |
| `nfc devices` | Prints devices returned by `devices.list_input_devices()`. |
| `nfc install-analyzers` | Installs both managed analyzer environments through `installer.py`. |
| `nfc install-analyzers --only birdnet` | Runs only the BirdNET installer path. |
| `nfc install-analyzers --only nighthawk` | Runs only the Nighthawk installer path. |
| `nfc record` | Creates a `Session` from saved config, starts it, and waits until it becomes idle or receives `Ctrl-C`. |
| `nfc record-once` | Starts one `Session` and waits for idle; intended for scheduled/background invocation. |
| `nfc analyze /path/to/file.wav` | Calls `session.analyze_existing()` for one WAV file and prints JSON results. |
| `nfc backfill 2026-05-10` | Finds the matching night folder and calls `analyze_existing()` for each WAV in its `audio/` directory. |
| `nfc autoschedule --enable` | Calls the platform autoschedule installer using the saved start time. |
| `nfc autoschedule --disable` | Calls the platform autoschedule uninstaller. |
| `nfc prepare-ebird /path/to/night --state-province MA` | Regenerates upload and review CSVs from saved results; use `--help` for location and checklist options. |
| `nfc precipitation /path/to/night` | Refreshes the comparable 18:00–06:00 local precipitation report. |
| `nfc web` | Starts the local FastAPI web app with browser launch enabled. |

The `nfc-tools` command launches the web app and opens the browser.
`nfc-tools-dev` selects an isolated development profile before launch, with its
own configuration and data paths. Its output must stay under
`~/Desktop/nfc-tools-dev-output`. It defaults to BirdNET only; the normal profile
defaults to BirdNET, Nighthawk, and wingbeat screening. See
[profile and upgrade details](docs/birdnet-3-upgrade.md).

## Repository map

[CODEBASE.md](CODEBASE.md) and the folder READMEs describe the full file layout.
Start with these modules when tracing behavior:

| Area | Main modules |
| --- | --- |
| Configuration and paths | `config.py`, `paths.py` |
| Recording and scheduling | `session.py`, `recorder.py`, `sounddevice_recorder.py`, `schedule_resolver.py`, `segments.py`, `autoschedule.py` |
| Imports and recovery | `importer.py`, `night_status.py`, `lock.py` |
| Analyzers | `installer.py`, `analyzers/`, `birdnet_policy.py`, `birdnet_version.py` |
| Clips and metadata | `clip_exporter.py`, `clip_metadata.py`, `filenames.py` |
| eBird exports | `ebird_export.py`, `ebird_locations.py`, `ebird_rarity.py`, `birdnet_taxonomy.py` |
| Weather and acoustic estimates | `weather.py`, `precipitation.py`, `acoustics.py` |
| Web interface | `web/server.py`, `web/routes*.py`, `web/templates/`, `web/static/` |

Module paths above are relative to `src/nfc_tools/`. Runtime taxonomy data lives
in `src/nfc_tools/data/`; Markdown references in `docs/reference/` are not loaded
by the application. Keep runtime mappings and their documentation consistent.

## Current web UI structure

The main navigation is defined in `src/nfc_tools/web/templates/base.html`.

Current nav order:

```text
NFC Tools
Night Summary
Settings
Readiness Check
Import Recordings
Auto-record
Diagnostics
```

Templates and their browser controllers share descriptive names, such as
`nights.html` / `nights_page.js` and `import_recordings.html` / `import_page.js`.
`dashboard.html` uses `app.js`. The shared `ebird_location.html` and
`ebird_location.js` controls serve Settings and imports. Layout styles live in
`style.css` and `settings_page.css`. See the [web code guide](src/nfc_tools/web/README.md)
for route and file responsibilities.

Auto-record has automated coverage, but real overnight launch still needs
hands-on validation.

Check UI examples against the current running app before committing them.

Avoid reintroducing older experimental dashboard scripts such as:

```text
dashboard_live_status.js
dashboard_live_status.css
dashboard_status.js
dashboard_status.css
```

Dashboard status and meter behavior live in `app.js`.

## Import Recordings

**Validation scope:** automated tests cover conversion, import recovery, and
output generation. They substitute test doubles for Nighthawk and BirdNET.
Passing those tests does not establish end-to-end inference quality or overnight
reliability; validate those with representative recordings.

Successful completion of an entire import batch plays the bundled “Slow ding”
by KoiRoylers, even if the browser page is closed. Set
`notifications.on_batch_complete: false` to disable it. Playback runs in a
background thread and failures do not fail the import. See the
[sound credits](src/nfc_tools/data/sounds/README.md) for attribution and license.

The import workflow lets users select analyzers, choose source/output folders,
set the recording location, correct the timeline, confirm storage, and start a
background job. Original audio is never modified.

The scan reads durations from WAV headers or FFmpeg when available and groups
AIF/AIFF and WAV/WAVE names consistently. Timeline review includes every scanned
file and supports bulk clock correction and manual edits. Times use validated
24-hour text fields; browser timezone must not alter the entered wall-clock time.
Changing times invalidates timeline and storage confirmation.

The map and saved import location are independent of Settings. Storage estimates
cover processed audio, analyzer results, and clips. Setup controls are disabled
while a job is being submitted, run, or resumed.

`importer.py` validates the complete reviewed source list, timestamps, file size/mtime,
location/timezone, enabled analyzers, and estimated PCM space. It snapshots Config
without saving Settings, converts source slices with FFmpeg, and calls
`Session._analyze_one()` for analysis, clips, and manifests. That method returns
per-analyzer statuses so a failed import segment is never counted as complete.

Import step 1 selects any combination of Nighthawk, BirdNET, and possible wingbeats.
Steps 2–6 are folders, session details, timeline review, output/storage, and run monitor.
Nighthawk and BirdNET selections start from Settings; WING starts checked for a new import. Selections apply only to that import and survive pause/resume.
`enabled_analyzers` is a validated, nonempty list at job preparation; it takes precedence
over the legacy `wingbeats_enabled` field. Old requests that omit the list retain the
Settings/legacy wingbeat-toggle behavior. Changes require timeline/storage confirmation again.

Import and live analysis use the same `Session._analyze_one` and clip exporter:
`<night>/audio/*.wav`, `results/<analyzer>/<recording>/`,
`audio/clips/<segment-folder>/*.wav`, `logs/`, and `manifest.csv`. Optional eBird
exports go to `results/eBird checklists/`; otherwise review CSVs go to `review/`.
See [clip files and context](#clip-files-and-context) for segment-folder naming.
The wingbeat detector writes CSV and Audacity labels and creates contextual review clips just
like other analyzers. Imports additionally keep `.nfc-imports/` checkpoints and
source metadata at the output root, and fetch historical environmental data
instead of live weather. Clips are created only when detections exist.

The worker writes atomic JSON checkpoints beneath `<output>/.nfc-imports/<uuid>/`.
Start request UUIDs are idempotent. A process mutex prevents simultaneous jobs;
an OS output-folder lock also prevents concurrent importers across processes and
releases on process exit. Pause happens between segments. Recovery skips completed
segments, reuses published audio, and retries unfinished analysis. Source identity
is checked again before each conversion. Existing output files are never overwritten.
Removable filesystems without hard links use exclusive file creation; an abrupt power
loss during that fallback copy may require removing the incomplete segment named
in the error before resuming.

### Import API and progress

| Method and path | Purpose |
| --- | --- |
| POST `/import-recordings/start` | Prepare/start the reviewed import. |
| GET `/import-recordings/run` | Current status; accepts `output` and `job_id` for recovery. |
| POST `/import-recordings/run/{job_id}/pause` | Pause after the current part; accepts an `output` form field. |
| POST `/import-recordings/run/{job_id}/resume` | Resume a saved job; accepts an `output` form field. |
| GET `/import-recordings/run/{job_id}/plan` | Retrieve the saved plan. |
| GET `/import-recordings/run/{job_id}/log` | Read `events.jsonl` using `output` and a byte `cursor`, up to 200 entries per response. |

The page saves the last job ID and output folder in localStorage. Checkpoint
folders also provide the UUID needed for recovery. Progress reports completed
recordings, audio duration, part counts, and the current analyzer start time.
It does not estimate progress within an analyzer. The event log includes
heartbeats, analyzer steps, clip output, weather availability, and errors; it is
not raw analyzer stdout.

### Import settings and weather

`birdnet_year_round` defaults to false for new jobs. The seasonal week comes
from the corrected date in each generated WAV filename: four weeks per month,
clamped to 1–48. Year-round mode omits the analyzer
`--week` argument while retaining coordinates. With sensitivity overrides, the
species-list helper receives no seasonal week and its list is passed with `--slist`. Old checkpoints
without this field keep year-round filtering. The recorder Settings page also exposes
the option; import choices are independent and captured with the import plan.

Imports call `environmental_snapshot(..., historical=True)` before part analysis and
checkpoint its completion. Historical requests use UTC timestamps to disambiguate DST
and select the correct UTC date, while the saved row keeps the local recording time.
Recent historical data uses the [Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api),
which includes pressure-level wind. Pre-2022 data uses the surface reanalysis archive;
missing upper-air fields remain unavailable. Weather lookup failures are logged and
do not prevent analysis. Weather requests retry transient Open-Meteo failures; when a
failed row is later backfilled, the eBird exporter prefers the successful row for
checklist comments. Tests mock weather and Nighthawk/BirdNET inference; real-world validation remains
necessary.

### Import verification

Import tests use real FFmpeg conversion and clip export with Nighthawk/BirdNET
test doubles. The wingbeat integration test uses the real detector on synthetic
pulses and compares import output with the live analysis path. Browser tests
cover analyzer selection, restored plans, output-folder changes, and recovery.
A recording is complete only when every part has finished. Pausing means
“pause after the current part,” not interrupting inference.

### Import validation and draft preservation

Changing the output folder preserves session fields, timeline corrections, and
clock-shift controls, but requires a new storage check. A failed scan preserves
the draft. A successful rescan reuses entries only when path, relative filename,
size, and modification time match. Added or modified files require timeline
review; a new source folder or explicit new import resets the timeline.

Delayed recovery responses must not replace a newer draft. Both status and plan
fetches recheck the current page state after awaiting a response. Regression
coverage lives in `tests/test_import_timeline.cjs`.

## Recording and analysis flow

The core pipeline is:

```text
Dashboard / CLI
  -> Session
  -> Recorder
  -> completed WAV segment
  -> analyzer queue
  -> enabled analyzers (Nighthawk, BirdNET, optional wingbeat detection)
  -> results/
  -> audio/clips/
  -> manifest.csv
```

On macOS, `recording.backend = auto` uses the sounddevice/CoreAudio path for normal recording. The ffmpeg/avfoundation path remains available as a fallback and diagnostic comparison path.

Recording segment boundaries are centralized in `src/nfc_tools/segments.py`.
`recording_period_and_seconds()` recalculates solar events for the recording's
local date and splits at the earliest upcoming boundary or configured segment
length. Boundaries include astronomical and civil twilight, sunrise plus two
hours, midnight, and noon (the night-folder rollover). Recorders and imports use
this date-aware handling for long recordings, with a two-second tolerance when
assigning period labels.

New recordings with timezone information use
`<index>_<period>_<YYYY-MM-DD>_<HH-MM-SS>_UTC<±HHMM>.wav`.
The explicit UTC offset distinguishes repeated local times when daylight saving
time ends. Legacy names without an offset remain readable.
Periods are `NFC` (astronomical dusk to astronomical dawn), `CIVIL_MORNING`
(astronomical dawn to civil dawn), `MORNING_FLIGHT` (civil dawn to sunrise plus
two hours), `DAYTIME` (sunrise plus two hours to civil dusk), and `CIVIL_EVENING`
(civil dusk to astronomical dusk). Only the strict nighttime period uses `NFC`
in new filenames. `filenames.py` continues to parse legacy prefix-based names,
including `NFC_CIVIL_EVENING` and `NFC_CIVIL_MORNING`.

The dashboard's **Include morning flight recordings** option persists as
`schedule.include_morning_flight`, defaulting to false. `schedule_resolver.py`
extends the resolved stop to sunrise plus two hours without shortening a later
scheduled stop. The option also applies to automatically scheduled sessions;
change it while idle. The dashboard separately previews the NFC counting end
and the recording stop. **Record now even outside the scheduled window** remains
an independent option and does not expand the NFC counting window.

Deferred overnight processing completes bird analysis across the queued files,
then publishes bird exports before processing WING candidates. Existing bird
exports remain available during WING processing. Single-file analysis, including
imports, likewise publishes bird results before WING for that file; it does not
reorder the entire import batch into separate bird and WING passes. Sleep
prevention is released after the final deferred analysis finishes.

The activity log shows timestamps and plain-language actions, newest first,
with later events first within the same second. Recording and analysis events
include filenames. Progress uses per-analyzer “Done with x of y recordings”
counts without a redundant remaining count. Keep `tests/test_live_progress.cjs`
in browser verification when changing this presentation.

### Durable night analysis and recovery

`logs/analysis_progress.json` checkpoints each recording by size and modification
time, with separate analyzer and clip-export states and a night eBird export
state. Writes use a flushed temporary file and atomic replacement, serialized by
the existing night analysis lock. A running/failed/pending stage is retryable;
completed inference is skipped, including when clip export failed afterward.
Changed audio resets its checkpoints. Missing recorded analyzer artifacts trigger
recovery; corrupt checkpoint JSON is reported rather than silently discarded.

`night_status.py` derives coverage from original scheduled/started log windows and
validated WAV durations; it merges overlapping intervals and reports gaps longer
than two seconds. Missing expected-window history is explicitly unknown. Files
referenced by manifests/checkpoints but absent on disk are reported as missing.
Crash-truncated WAVs are excluded from valid coverage and automatic analysis.
The Night Summary UI refreshes during active work and exposes a manually requested
recovery worker; no background recovery starts just because the app launches.

`night_status.write_status_files()` writes `NIGHT_STATUS.txt` and segment-level
`audio/clips/<segment-folder>/STATUS.txt` snapshots. Completed zero-clip analysis is distinct
from pending or failed analysis; a clip folder may contain only its status file.
Snapshots include an update timestamp and may change as work continues.

Clip exports keep stable per-label occurrence names and replace completed clips
atomically, avoiding numbered duplicates after a retry. Historical manifest-only
successes retain inference and regenerate clips once because old versions did not
checkpoint clip completion. Recovery uses the currently configured analyzers and
site settings; it does not claim that changed analysis settings were applied to
previously completed work. CLI `nfc analyze` remains an explicit rerun.

## Analyzer outputs and clip export

Managed install commands in `installer.py` pin BirdNET Analyzer to commit
`032dcaca6afb2a3438965f80d5e01de0fb2036b4`, `birdnet` to `1.4.0`, and
Nighthawk to `0.3.1`. BirdNET uses a private Python 3.11 micromamba environment;
an existing compatible installation is reused. Update the installer requirements
and model-identity checks only after checking compatibility,
and record deliberate bumps in `CHANGELOG.md`. Nighthawk uses a Python 3.10 venv
when the app runs on 3.10, otherwise a managed Python 3.10 micromamba environment;
an existing valid mamba environment is reused before either install path.
`tests/test_installer.py` verifies the pinned commands for BirdNET and both
Nighthawk install paths. These tests mock installation; they do not download or
validate upstream models.

Both app profiles use the BirdNET `3.0` acoustic model (preview 3.1).
The production install lives in `analyzers/birdnet3`, leaving `analyzers/birdnet`
untouched for the previous app. Profile isolation controls paths and scheduling,
not the model version. Existing imports and nightly analysis checkpoints must
match the pinned model and software identity before resuming. Legacy work must
finish in the old app or be imported into a fresh output folder.

Analyzer adapters write per-recording results under:

```text
<night>/results/<analyzer>/<recording-stem>/
```

Nighthawk is invoked with Raven and Audacity output enabled. The clip exporter treats Nighthawk's Audacity label files as the source of truth for clip start time, end time, and label text.

### BirdNET confidence and seasonal filtering

`birdnet_min_conf` defaults to 0.500. Saved settings take precedence. The adapter
requests both CSV and Raven table output. Clip export prefers
`.selection.table.txt` files, then falls back to parseable tables or CSVs if no
table clips are found.

`birdnet_policy.py` defines the shared filtering rules. Winter finch and owl
sensitivity are independently optional and default to off. When enabled:

- The selected species are added to the normal location/date species list.
- BirdNET runs at the lower of the general threshold and 0.25.
- Result filtering and clip selection keep the lower threshold only for the
  selected species; other species still need the general threshold.
- `nfc_birdnet_policy.json` records the model, location, week, and filtering choices.

These options increase review volume and false positives; they do not confirm
identifications. Import plans preserve their settings. Reanalysis is needed to
recover detections excluded by an earlier run.

Seasonal filtering uses the recording date, with four weeks per month (1–48).
Year-round filtering keeps the location but omits the seasonal restriction.
Sensitivity overrides use an explicit species list instead of passing location
and week directly to the analysis command. See `analyzers/birdnet.py` and
`tests/test_birdnet_dates.py` / `tests/test_birdnet_sensitivity.py`.

### Clip files and context

Review clips are written on successful analyzer completion under:

```text
<night>/audio/clips/<local-HH-MM-SS>_UTC-<UTC-HH-MM-SS>/
```

Offset-bearing recordings use both local and UTC start times in the folder name.
Legacy recordings without an offset use only the local time.

Clip filenames follow the analyzer label style:

```text
swathr (0.943)-Nighthawk.wav
swathr (0.812)-BirdNET.wav
swathr (0.943)-Nighthawk 2.wav
```

`clip_exporter.py` adds four seconds before and after each detection, clamped to
the recording boundaries. A one-second detection produces up to nine seconds of
audio; a three-second detection produces up to eleven. The policy applies to
Nighthawk, BirdNET, and wingbeat review clips. Original analyzer intervals remain
unchanged. Ambient context helps listeners evaluate the sound before and after
the detection.

If Nighthawk or BirdNET output formats change, update `src/nfc_tools/clip_exporter.py` and `tests/test_clip_exporter.py` together. Tests should assert both the parsed analyzer intervals and the final ffmpeg `-ss`/`-t` values, including start/end-of-file clamping.

### Experimental wingbeat screening

See the [wingbeat detector README](README_WINGBEATS.md) for the user-facing explanation and source credits.

**Possible wingbeats** is included in normal-profile configuration defaults and
preselected for new imports. The isolated development profile defaults to BirdNET only. Saved live analyzer selections and restored import plans remain authoritative. Change it under Settings → Analyzers (or add
`wingbeats` to `analyzers.enabled`). It uses the app’s NumPy dependency and
FFmpeg without a model download. Recording and import analysis both run it
through the normal analyzer registry, progress tracking, and retry flow.
`installer.status()` reports it as installed with `builtin: true`; Settings,
Diagnostics, and Readiness share that status. There is no separate WING installer.
FFmpeg availability is checked separately as the shared audio engine.

Wingbeat screening reads the full recording, including recordings that produce no
candidates. `Session._analyze_one` supports explicit analyzer subsets for the
bird-first queue described above; imports use its per-file ordering. WING analysis
and clip export therefore add to total processing time. No comparative runtime
benchmark establishes parity with Nighthawk; relative runtime depends on the
computer and recording. Avoid documenting a fixed Nighthawk-to-WING time ratio.

`analyzers/wingbeat_frames.py` caches frame-local FFT spectra, spectral medians,
and frequency masks across overlapping windows. Each stream owns caches bounded
to the current two-second region; window-dependent statistics, thresholds,
window scheduling, candidate intervals, and scores remain unchanged.
`tests/test_wingbeat_frames.py` checks exact cached/uncached equivalence and cache
bounds. Reproduce the screening-only comparison with
`python scripts/benchmark_wingbeats.py --seconds 35 --repeats 3 <recordings...>`.
See the [October 22 performance report](docs/evaluations/wingbeat-performance-2026-10-22.md)
for local measurements and limitations; this is not an accuracy improvement or
a comparison with Nighthawk.

The detector streams mono 24 kHz audio through two kinds of screening:

- **Broadband pulses:** repeated low-frequency energy with matching rhythms
  across several frequency bands.
- **Spectral accompaniment:** repeated energy near a spectral peak, supported by
  surrounding noise and additional checks intended to reject tonal interference.

The stream retains at most two seconds of audio. It evaluates overlapping
2-second, 1.5-second, and 1-second windows, with additional accompaniment passes
every 0.25 seconds. Overlapping detections merge using the furthest end time.
Legacy 8 kHz callers use the broadband path only.

Thresholds, frequency bands, and conditional rhythm/spectral checks are defined
in [`wingbeats.py`](src/nfc_tools/analyzers/wingbeats.py) and
[`wingbeat_accompaniment.py`](src/nfc_tools/analyzers/wingbeat_accompaniment.py).
Use those definitions when changing the detector instead of copying thresholds
from historical reports. The reports explain why particular checks were added:

- [Initial screening evaluation](docs/wingbeat-screening-evaluation.md)
- [Localized-pulse evaluation](docs/evaluations/wingbeat-localized-2026-10-11/report.md)
- [Brief-window evaluation](docs/evaluations/wingbeat-annotation-candidate-2026-10-11/report.md)
- [Waterfowl evaluation](docs/evaluations/wingbeat-waterfowl-2026-10-16/release-report.md)

These use selected recordings and do not establish general field accuracy.
The research scanner shares the production window schedule and writes an
`analysis_pass` field. Use a fresh research output directory after detector changes.

These bands and thresholds are provisional engineering choices, not validated
biological boundaries. Overlapping candidates merge into review intervals.

Results live in `results/wingbeats/<recording>/`: a `*_wingbeats.csv` with code
`WING`, `review_required=true`, and a periodicity score, plus Audacity labels.
The score measures repeated-pattern similarity; it is not identification
confidence. The existing clip exporter adds four seconds of context on either
side. WING also appears in review CSVs, with no species mapping or confidence,
and never contributes to NFC counts or eBird import rows.

This is a screening heuristic, not a trained wingbeat classifier. Rhythmic rain,
machinery, rustling, or other pulsed sounds can trigger it. Quiet, brief,
irregular, or out-of-band wingbeats can be missed; stereo downmixing can also
cancel opposite-phase sounds. Synthetic tests validate software behavior only.
See [detector evaluation](docs/wingbeat-screening-evaluation.md) for the supplied
recording check, synthetic controls, and the reproducible evaluation command.
Before relying on it, compare flagged and unflagged intervals against manually
labeled recordings from the actual microphone and site, and measure precision
and recall. Relevant acoustic background: [Wing-Beat Frequency and Its Acoustics in Birds and Bats](https://pubmed.ncbi.nlm.nih.gov/32573685/).

## Dashboard meter

The dashboard meter uses one visual mapping in both standby and recording states:

```text
input level -> dBFS -> percentage -> green/yellow/orange/red ramp
```

`app.js` polls the backend meter every 250 ms and renders the latest reading on
a separate 150 ms timer, without interpolating between readings. During recording,
levels come from the recording stream; standby uses a microphone preview.
Metering pauses when the page is hidden or after 30 seconds of user inactivity.
This pauses the meter, not an active recording.

### Readiness sample volume checks

Readiness measures the saved three-second test clip with FFmpeg, retaining its
playback/download link for all outcomes. A peak at or below -90 dBFS flags silent
or nearly silent audio as a problem; an average below -60 dBFS flags very low
input as a note. These are input-level checks, not a judgment of call quality;
a quiet site can legitimately trigger the low-volume note. A failed level check
also produces a note and leaves the sample available for listening. The saved
sample's measured status is also applied to the input-signal row.

## CSV date and time convention

CSV files that report date and time should use separate columns:

```text
date,time
2026-06-13,16-11-31
```

Use `yyyy-mm-dd` for dates and 24-hour `hh-mm-ss` for times in application CSV
logs. External formats, including analyzer output and eBird imports, follow
their own specifications. JSON metadata and checkpoints may use ISO timestamps.

## eBird checklist exports

Live sessions and imports write exports under `results/eBird checklists/` when
eBird exports are enabled and the required location codes are configured.

| File | Purpose |
| --- | --- |
| `ebird_record_import_yyyy-mm-dd_hh-mm.csv` | One recording's upload rows. |
| `ebird_review_yyyy-mm-dd_hh-mm.csv` | The corresponding review rows. |
| `ebird_record_import_night_yyyy-mm-dd.csv` | Combined upload rows for the night. |
| `ebird_review_night_yyyy-mm-dd.csv` | Combined review rows for the night. |

Per-recording names use the recording's start time without seconds. A combined
upload may create several checklists. Upload CSVs omit headers and UTF-8
byte-order marks; review CSVs include both for spreadsheet use. See the
[eBird import reference](docs/reference/nighthawk-species-family-lookup.md).

A missing state/province is a readiness note, not a recording or analysis blocker.
Export validation requires a 1–3 character state/province code such as `MA` and a
two-letter country code. With exports disabled, general review CSVs go to `review/`.

The packaged `data/nighthawk_ebird_taxonomy.csv` maps Nighthawk species, slash
taxa, families, and broad call types to eBird-compatible names. The
[reference](docs/reference/nighthawk-species-family-lookup.md) documents its
source and unresolved mappings. Preserve identification scope: do not turn a
slash taxon or broad call type into a single species automatically. The Markdown
reference itself is not runtime input.

Upload rows use accepted common names, leave `Genus` and `Species` blank, and
have no additional family column. Detection counts belong in species comments,
not individual-bird counts. Users still complete eBird's species and location
matching after upload.

Species comments use `NFC <count>` for the combined Nighthawk and BirdNET
detection total during the strict NFC period and `Flight call <count>` outside
it. Both model counts follow as `Nighthawk detections <count>` and
`BirdNET detections <count>`, including zero counts. Totals count model detections,
not deduplicated unique calls: a call detected by both models contributes twice
and requires manual review. Wingbeat detections do not contribute to these totals.
Outside-window checklists add the corresponding Evening twilight, Morning
twilight, Morning, or Daytime flight-call comment. Periods remain separate,
incomplete checklists. The exporter provisionally retains the NFC protocol
outside the counting window; this is application behavior pending eBird guidance,
not confirmation that eBird endorses daytime remote recordings under that protocol.
WING candidates remain in review CSVs and are excluded from upload CSVs.

Checklist comments mark starts and stops at civil twilight, astronomical
twilight, and midnight, then add weather conditions. The exporter uses the
filename start and actual WAV duration, with a two-second boundary tolerance.
It uses recording-site coordinates and timezone even when exports target a
hotspot. Missing or unreadable audio does not receive inferred boundary notes.

Preserve existing comments and avoid duplicate phrases. Join comment parts with
` | ` in the CSV. Tests should cover both sides of each boundary, recordings
with neither or both endpoints on a boundary, and repeated export generation.
See the [civil twilight rules](docs/reference/nighthawk-species-family-lookup.md#civil-twilight-checklist-comments).
The eBird import format takes precedence over the application's CSV log conventions.

### Optional eBird location association

`Site.ebird_export_enabled` controls checklist creation. `None` and `True`
enable exports; only `False` disables them. A missing state/province produces a
readiness note and blocks checklist export. Disabled exports still produce
review CSVs, including wingbeat candidates, under `review/`.

Settings and imports share `ebird_location.html` / `ebird_location.js`. Users
choose a personal location to match later in eBird, or search for a public
hotspot. Recording coordinates remain separate from export coordinates. Only
server-returned or previously saved hotspot details can be selected. CSV upload
cannot itself bind a checklist to an eBird location ID; users still complete
eBird's location-matching step.

`/api/ebird/hotspots` uses an explicit API key, a saved local key, or
`EBIRD_API_KEY`, in that order. A successful explicit key is saved atomically as
`ebird-api-key` in the config directory, with owner-only POSIX permissions. This
file is not encrypted and is excluded from config YAML, import plans, and
diagnostic bundles. The browser receives availability flags, never the saved key.
Hotspot results are cached in memory, so a new search may be needed after restart.

GET `/api/ebird/key` reports key availability; DELETE `/api/ebird/key` removes
the local key. `tests/test_ebird_locations.py` and
`tests/test_ebird_location.cjs` cover persistence, replacement, rejected keys,
forgetting, browser feedback, and exclusion from diagnostics.

### BirdNET taxonomy mapping

BirdNET names are translated through a [versioned eBird crosswalk](docs/reference/birdnet-ebird-crosswalk.md). Review CSVs retain original names and show `taxonomy_status`, `taxonomy_reason`, and `taxonomy_version`. Uncertain matches are flagged for review and excluded from upload files; candidate matches are shown separately. Regenerate exports to apply the current crosswalk to existing analysis results.

### Regional rarity filters

#### Supported input structure

- UTF-8, comma-separated CSV with no header row, no larger than 2 MiB.
- First column: exact eBird common name. Names must be unique within the file.
- Remaining columns: alternating date and threshold pairs. Each row must have at
  least one pair; different taxa may have different numbers of pairs.
- Each row begins with `Jan 1`. Subsequent dates must be strictly increasing,
  without duplicates.
- Dates use English three-letter month names and day numbers, such as `Sep 30`.
  Years are omitted because thresholds repeat annually.
- Thresholds are nonnegative whole numbers. Blank or fractional counts are not
  supported.
- Quoted names, a UTF-8 byte-order mark, and Windows line endings are supported.
  Blank rows are ignored, and surrounding cell whitespace is stripped.
- February 29 change points are not supported. Recordings made on February 29
  are evaluated normally using the threshold already in effect.

Synthetic example (not actual reviewer data):

```csv
Example bird,Jan 1,0,May 1,20,Oct 1,0
Another example bird,Jan 1,0
```

For the first row, zero-threshold periods are January 1–April 30 and October
1–December 31. The second row has a zero threshold all year.

#### Interpretation and matching

Each threshold takes effect on its listed date and continues through the day
before the next date; the last threshold continues through December 31.
Positive thresholds must remain in the imported data because they end zero
periods, even though NFC Tools does not generate high-count warnings.

Only a zero threshold adds this exact sentence to existing species comments:

> Flagged rare for species and/or date. Provide recording or description of the call.

Matching uses each recording's local start date, also written into its eBird
checklist. A September 30 recording at 11:35 p.m. uses September 30's threshold;
the following October 1 recording at midnight uses October 1's threshold, even
when both recordings share an overnight folder. Imported recordings use their
corrected local dates.

Names absent from the filter are **not evaluated**. Matching is exact, with no
fuzzy matching or automatic taxonomy aliases. A species-specific rule is not
applied to a broader identification with a different name.

#### Local handling and limitations

Import the CSV in Settings, provide its region, confirm coverage for the recording
and eBird location, and enable reminders. Parsed data is copied into the local
configuration, so moving the original file does not break the filter. Invalid
uploads are rejected with an error and preserve the previously saved filter.

The filter is optional and off by default. Changing location requires checking
coverage again. Review CSVs record the evaluation, applicable date interval,
region, source filename, import timestamp, and source checksum. These results
reflect the imported data and may differ from eBird's current filters.

Users can add recordings or call descriptions in eBird after upload; there is no
pre-upload documentation requirement in NFC Tools. Reviewer data is not bundled
with the application or this reference. Keep actual reviewer files and local
configuration/import snapshots out of the repository; use synthetic examples
for public documentation and tests.

### Weather-only acoustic checklist estimates

Live and imported recordings use the starting hour's weather to save an acoustic
score and descriptor in `logs/environmental_conditions.csv`. Checklist comments
include the descriptor and a link to the acoustic forecast website. Existing logs without acoustic results export an unavailable descriptor;
new rows upgrade the CSV schema without rescoring old recordings.

The calculation in `acoustics.py` adapts NFC acoustic environment forecast v2.2.12
(MIT). Its seven weather factors, fixed seasonal baselines, estimated 2 m wind,
gust caps, visibility fallback and half-point descriptor rounding are retained.
Foliage and insect effects are zero because neither is assessed. Scores therefore
range from 0.75 to 9.25 before display rounding; missing required inputs produce
unavailable, not a favorable default. These are modeled weather estimates, not
measurements of the audio. Model version and inputs are saved for reproducibility.

## Clip metadata

Exported WAV clips carry embedded metadata without changing their filenames: call time,
source recording and detection/clip offsets, configured site, analyzer suggestion and
score when available, and NFC Tools version and repository
link. A readable summary is stored in WAV `LIST-INFO` comments; the `nfct` chunk
contains UTF-8 JSON using schema `nfc-tools.clip`, version 1. Compatible metadata
inspectors can display the comment; ordinary players may ignore these fields.

Call timestamps come from the source filename, including its UTC offset when present.
Legacy filenames without an offset are explicitly marked as having an unknown timezone.
Site values describe the configuration used at export. The metadata writer
currently stores detector `model_version` as null. Weather and acoustic conditions
are not included in this first version.
Metadata is added to newly exported clips; existing clips are unchanged until re-exported.

Clip metadata records the original detection and analyzer suggestion. It does not include review status, reviewer identity, accepted/rejected decisions, confirmed identification, or review notes.

## Git and local generated files

The repository `.gitignore` covers local Python environments, caches, backups, patch scripts, WAV audio, recorder logs, and diagnostic artifacts. Other research tables, archives, and logs are not universally ignored; review `git status` before staging generated files. Create `.venv` locally after cloning or downloading the repository; it is not part of the source tree.

The original root handoff ZIP and the three tables under
`research/archive/2026-09-wingbeat-handoff/data/` were removed from the current
tree on September 26, 2026. Download the unchanged data from the
[research-data release](https://github.com/AndrewW-NFC/NFC-tools/releases/tag/wingbeat-research-data-2026-09-26)
and follow the [restore instructions](research/archive/2026-09-wingbeat-handoff/README.md#restore-the-research-data)
before running research commands that use those tables. Restored `data/` files
and release ZIPs downloaded into the bundle directory are ignored. Documentation
and the integrated scanner remain in Git; the superseded root scanner was
removed. No history rewrite was performed, so historical clones still include
the old data objects.

## Maintenance regression checks

Diagnostics file routes reject session dates outside the `YYYY-MM-DD` format
before calling `night_dir`; tests check both the 400 response and absence of
filesystem side effects. Twilight resolution logs a warning before falling back
to fixed times. Keep those cases covered by `tests/test_web_server.py` and
`tests/test_schedule_resolver.py`.

On Windows, `lock.py` opens the owner process with `SYNCHRONIZE` access and polls
with `WaitForSingleObject(handle, 0)`, closing the handle afterward. Access denial
preserves the lock; an exited process permits recovery even while another handle
still exists. The POSIX path retains `os.kill(pid, 0)`. Never replace the Windows
probe with that signal call: real Windows CI reproduced process termination or
incorrect stale-lock takeover before the fix.

## Research listening-review workspace

This is a research tool for the prepared waterfowl pilot, not the normal app's
recording-review workflow. It requires the external audio archive and catalog;
cloning this repository alone does not supply them.

`python -m nfc_tools.review open --root "/Volumes/T7/Wingbeats detector"`
starts or reconnects to that pilot at `http://127.0.0.1:8877`. Replace the example
root with the location of the prepared research data.
Add `--open-browser` to open it automatically. The `prepare` action builds a new
batch and refuses to overwrite one; `serve` runs its local server directly.
Annotations live under `reviews/<batch>/`, with an authoritative SQLite database,
revision history, and JSON backups. Listening copies stay under `audio-library/`.
Keep the drive mounted and wait for Saved before stopping the server.

The October 16 detector evaluation and reproducible verification scripts are in
`docs/evaluations/wingbeat-waterfowl-2026-10-16/`. See `release-report.md` there
for real-audio results and the added review-workload tradeoff. The target is
mechanical wing sounds for listener review, including wing–water contact, with
no requirement to assign behavioral categories. See [the October 16 work summary](docs/archive/2026-10-16-work-summary.md)
for collection and review work completed alongside the detector change.
