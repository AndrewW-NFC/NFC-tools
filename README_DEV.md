# NFC Tools — Developer notes

These notes are for people modifying NFC Tools itself. For end-user instructions, see `README.md`.

NFC Tools is usable but not yet well-tested outside MacOS. The codebase includes support paths for MacOS, Linux, and Windows. MacOS is the best-tested platform and has been used successfully many times. Linux appears to work in an Ubuntu virtual machine, but has not yet been used for real overnight recording. Windows is covered by automated tests, but has not yet been tested successfully in real-world use. Be cautious when changing code that touches microphones, native folder picking, automatic scheduling, analyzer installation, analyzer result parsing, clip export, CSV output formats, environmental condition output formats, or browser permissions.

## Quick setup

Clone the repository:

```bash
git clone https://github.com/AndrewW-NFC/NFC-tools.git
cd NFC-tools
```

Create and activate a virtual environment.

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

Run basic checks:

```bash
python -m compileall src/nfc_tools
pytest -q
nfc doctor
```

The test suite includes mocked Windows/Linux coverage for scheduling, sleep prevention,
ffmpeg backend selection, and device-enumeration parsing. Real microphone access,
systemd user timers, Windows Task Scheduler, and packaged-app launch still need
hands-on testing on those operating systems before release claims should be strengthened.

If Node.js is available, syntax-check the main browser scripts:

```bash
node --check src/nfc_tools/web/static/app.js
node --check src/nfc_tools/web/static/diagnostics_page.js
node --check src/nfc_tools/web/static/import_page.js
TZ=America/New_York node --test tests/test_import_timeline.cjs
TZ=Pacific/Auckland node --test tests/test_import_timeline.cjs
node --check src/nfc_tools/web/static/settings_page.js
```

Node.js is not required to run NFC Tools.

## Cross-platform checks

GitHub Actions runs the basic project checks on Ubuntu, Windows, and macOS for
every push and pull request. The workflow lives at `.github/workflows/ci.yml`.

The CI job installs NFC Tools in editable development mode, compiles the Python
package, runs the pytest suite, and syntax-checks the main browser JavaScript
files. These checks are intended to catch portable-code problems early, such as
path handling, case sensitivity, shell differences, and dependency issues.

CI does not replace real operating-system testing for microphone access,
systemd user timers, Windows Task Scheduler, packaged-app launch, or attached
audio/NFC hardware.

## Running the app in development

Launch the normal local browser app:

```bash
nfc-tools
```

Launch only the local web app:

```bash
nfc web
```

Run the FastAPI app with reload:

```bash
uvicorn nfc_tools.web.server:create_app --reload --factory
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
| `nfc web` | Starts the local FastAPI web app with browser launch enabled. |

The `nfc-tools` command launches the web app and opens the browser.

## Repository map

Important files and directories:

```text
docs/reference/nighthawk-species-family-lookup.md
  Nighthawk code and family reference, eBird name changes, upload-format guidance, and future checklist-comment requirements. Documentation only; not loaded by the application.

pyproject.toml
  Package metadata, dependencies, optional dev dependencies, and console scripts.

src/nfc_tools/app.py
  GUI-style launcher. Starts the web app and opens the browser.

src/nfc_tools/cli.py
  Click-based command-line interface.

src/nfc_tools/config.py
  Pydantic config model and YAML persistence.

src/nfc_tools/paths.py
  Platform-aware app config/data/cache/log paths, plus user-facing Desktop night folders.

src/nfc_tools/scheduler.py
  Computes recording windows and session dates.

src/nfc_tools/session.py
  Coordinates scheduled start, recording, stop, per-segment analysis, clip export, status updates, session logging, weather logging, and manifest entries.

src/nfc_tools/clip_exporter.py
  Exports analyzer-defined review clips from Nighthawk Audacity labels and BirdNET selection tables.

src/nfc_tools/session_logging.py
  CSV-backed dashboard/session log. CSV date and time fields are separate columns.

src/nfc_tools/weather.py
  Open-Meteo weather/environmental condition logging. Writes both spreadsheet-oriented CSV rows and paste-ready plain-text condition lines.

src/nfc_tools/recorder.py
  ffmpeg segment-mode recorder. Tracks completed WAV files and queues final partial files on stop.

src/nfc_tools/sounddevice_recorder.py
  sounddevice / PortAudio / CoreAudio recording backend, preferred on macOS.

src/nfc_tools/sounddevice_common.py
  Shared sounddevice/CoreAudio device-selection, level-meter, and float WAV helpers.

src/nfc_tools/sounddevice_diagnostics.py
  sounddevice/CoreAudio diagnostic recording and dashboard preview-meter helpers.

src/nfc_tools/installer.py
  ffmpeg, BirdNET, and Nighthawk install/repair logic.

src/nfc_tools/analyzers/
  Built-in analyzer plugins and the analyzer registry.

src/nfc_tools/manifest.py
  Per-night manifest CSV with separate date and time columns.

src/nfc_tools/autoschedule.py
  User-level OS scheduler support: launchd, systemd --user, and Windows Task Scheduler.

src/nfc_tools/doctor.py
  Health checks used by CLI and Diagnostics page.

src/nfc_tools/web/server.py
  FastAPI app factory and uvicorn launcher.

src/nfc_tools/web/routes.py
  Main web routes: dashboard, session control, Settings, and install/repair.

src/nfc_tools/web/routes_diagnostics.py
  Diagnostics page, raw recording tests, device-list logs, and diagnostics bundle routes.

src/nfc_tools/web/routes_import.py
  Import scan, planning, start/status/pause/resume routes. Nanosecond mtimes travel as strings to avoid JavaScript integer precision loss.

src/nfc_tools/web/routes_schedule.py
  Auto-record page routes.

src/nfc_tools/web/templates/
  Jinja templates for the local browser UI.

src/nfc_tools/web/static/
  Browser JavaScript and CSS.

tests/
  Unit tests for config, scheduling, filename parsing, clip export, recording lifecycle, web routes, and power behavior.
```

## Current web UI structure

The main navigation is defined in `src/nfc_tools/web/templates/base.html`.

Current nav order:

```text
NFC Tools
Settings
Readiness Check
Import Recordings
Auto-record
Diagnostics
```

Important templates:

```text
dashboard.html
  Main recording dashboard.

settings.html
  Recorder site, map/location, microphone, recording format, analyzer choices, and install/repair.

readiness.html
  Readiness Check page for microphone, storage, power, analyzer, and environment checks.

import_recordings.html
  Staged review and bulk-processing page, with clock correction and run monitoring.

schedule.html
  Auto-record enable/disable page. Not yet tested.

diagnostics.html
  Health checks and diagnostics-bundle download.

```

Important static files:

```text
app.js
  Main dashboard behavior, meter, session start/stop, status rendering, install log handling.

diagnostics_page.js
  Diagnostics-page raw recording tests and device-list behavior.

import_page.js
  Import Recordings page: folder choosing, source scan, timeline correction, confirmations, submission, polling, and checkpoint recovery.

settings_page.js
  Settings-page map/location behavior and layout enhancement.

settings_page.css
  Settings-page-specific map and layout CSS.

style.css
  General app layout and UI styling.
```

Do not commit handcrafted UI mockups unless they have been captured from the
current running app and reviewed against it.

Avoid reintroducing older experimental dashboard scripts such as:

```text
dashboard_live_status.js
dashboard_live_status.css
dashboard_status.js
dashboard_status.css
```

Recent work consolidated dashboard status/meter behavior into `app.js`.

## Import Recordings

**Status: bulk processing is implemented but has not yet been tested in real-world use.** Automated tests and a browser walkthrough cover the implementation, but end-to-end validation with real recordings and actual BirdNET/Nighthawk inference remains outstanding.

The Import Recordings page uses a staged review before a background import job. It can:

```text
choose a source folder with the native folder picker
choose an output folder with the native folder picker
scan supported audio files without modifying originals before opening timeline review
group AIF/AIFF as AIFF and WAV/WAVE as WAV in user-facing format counts
read source duration from WAV headers or ffmpeg metadata when available
preview an import-specific recording location on a draggable map without saving Settings
read free space from the selected output location
show an early storage estimate for processed audio, analyzer results, clips, and total output
build a cautious timeline review from filename times or sequential durations
include every scanned file in the timeline for bulk clock correction
shift inferred wall-clock times independently of browser timezone, preserving manual edits
invalidate timeline and storage confirmation when times change
show current-step guidance, confirmed-step badges, and disable setup while submitting, running, or resuming a saved plan
use validated 24-hour text input instead of locale-dependent datetime-local widgets
remember the import location in browser localStorage, independently of Settings
write one per-session eBird upload CSV and one combined night upload CSV
```

`importer.py` validates the complete reviewed source list, timestamps, file size/mtime,
location/timezone, enabled analyzers, and estimated PCM space. It snapshots Config
without saving Settings, converts source slices with FFmpeg, and calls
`Session._analyze_one()` for analysis, clips, and manifests. That method returns
per-analyzer statuses so a failed import segment is never counted as complete.

The worker writes atomic JSON checkpoints beneath `<output>/.nfc-imports/<uuid>/`.
Start request UUIDs are idempotent. A process mutex prevents simultaneous jobs;
an OS output-folder lock also prevents concurrent importers across processes and
releases on process exit. Pause happens between segments. Recovery skips completed
segments, reuses published audio, and retries unfinished analysis. Source identity
is checked again before each conversion. Existing output files are never overwritten.
Removable filesystems without hard links use exclusive file creation; an abrupt power
loss during that fallback copy may require removing the incomplete segment named
in the error before resuming.

Endpoints: POST `/import-recordings/start`; GET `/import-recordings/run` (optional
`output` and `job_id` for recovery); POST `/import-recordings/run/{job_id}/pause`
or `/resume` with an `output` form field. The page saves the last job identifier
and output folder in localStorage. Runs can also be recovered using the endpoint
and UUID from their checkpoint directory.

GET `/import-recordings/run/{job_id}/plan` returns the immutable plan for reopening
the page. GET `/import-recordings/run/{job_id}/log?output=...&cursor=...` pages through
the append-only `events.jsonl` history using a byte cursor (200 entries per response);
the lighter UI does not show this full log by default. The log includes analyzer steps
and heartbeats, clip messages, weather availability, errors, part completions, and
full-recording completions. It is not raw analyzer stdout. The status endpoint reports
recording counts, completed audio duration, part counts, and the current analyzer
start time. No within-analyzer percentage is invented.

`birdnet_year_round` defaults to false for new jobs. BirdNET receives `--week` based
on the corrected date in each generated WAV filename: four weeks per month, clamped
to 1–48. Year-round mode passes `--week -1` while retaining coordinates. Old checkpoints
without this field keep year-round filtering. The recorder Settings page also exposes
the option; import choices are independent and captured with the import plan.

Imports call `environmental_snapshot(..., historical=True)` before part analysis and
checkpoint its completion. Historical requests use UTC timestamps to disambiguate DST
and select the correct UTC date, while the saved row keeps the local recording time.
Recent historical data uses the [Historical Forecast API](https://open-meteo.com/en/docs/historical-forecast-api),
which includes pressure-level wind. Pre-2022 data uses the surface reanalysis archive;
missing upper-air fields remain unavailable. Weather lookup failures are logged and
do not prevent analysis. Tests mock weather and analyzers; real-world validation remains
necessary.

Tests use real FFmpeg conversion and clip export with deterministic analyzer doubles;
model downloads and real BirdNET/Nighthawk inference are not part of the test suite.

The page follows these product rules:

```text
originals are never modified
users choose folders instead of typing paths
do not start processing until the timeline is correct
processed output should follow the normal NFC Tools night-folder structure
clip export matches normal one-night processing
pause means "pause after current part"; a recording is complete only after every part finishes
```

## Recording and analysis flow

The core pipeline is:

```text
Dashboard / CLI
  -> Session
  -> Recorder
  -> completed WAV segment
  -> analyzer queue
  -> BirdNET and/or Nighthawk
  -> results/
  -> clips/
  -> manifest.csv
```

On macOS, `recording.backend = auto` uses the sounddevice/CoreAudio path for normal recording. The ffmpeg/avfoundation path remains available as a fallback and diagnostic comparison path.

Recording segment boundaries are centralized in `src/nfc_tools/segments.py`. The astronomical twilight preset uses sun-altitude boundaries instead of fixed pre- or post-night buffers. A segment should stop at the earliest of the configured segment length, evening civil twilight, astronomical dusk, midnight, astronomical dawn, or morning civil twilight. Period labels are assigned from the segment start time with a small tolerance around NFC boundaries so recorder chunks near astronomical twilight still open the next file as `NFC_CIVIL_EVENING`, `NFC`, or `NFC_CIVIL_MORNING` as appropriate. Keep civil-to-astronomical twilight recordings separate from the strict astronomical-dusk-to-astronomical-dawn `NFC` period.

## Analyzer outputs and clip export

Analyzer adapters write per-recording results under:

```text
<night>/results/<analyzer>/<recording-stem>/
```

Nighthawk is invoked with Raven and Audacity output enabled. The clip exporter treats Nighthawk's Audacity label files as the source of truth for clip start time, end time, and label text.

BirdNET is invoked with both `csv` and `table` result types. The clip exporter prefers BirdNET's `.selection.table.txt` files because they include `Species Code`, then falls back to any parseable table or CSV output only if no table clips are found. BirdNET clip export applies `cfg.analyzers.birdnet_min_conf` again as a guardrail, even though BirdNET is already run with that same minimum confidence.

Review clips are written on successful analyzer completion under:

```text
<night>/clips/<recording-start-HH-MM-SS>/
```

Clip filenames intentionally follow the analyzer label style:

```text
swathr (0.943)-Nighthawk.wav
swathr (0.812)-BirdNET.wav
swathr (0.943)-Nighthawk 2.wav
```

NFC Tools intentionally exports clips that are longer than the raw analyzer intervals. The shared policy lives in `src/nfc_tools/clip_exporter.py`: each valid analyzer row gets 4 seconds of context before its begin time and 4 seconds after its end time, clamped to the source WAV duration. BirdNET's default table rows are usually 3 seconds long, so exported BirdNET review clips are normally up to 11 seconds. Nighthawk labels can be as short as 1 second, so a 1-second Nighthawk label exports as up to 9 seconds; longer Nighthawk labels export as the analyzer label duration plus up to 8 seconds of context.

Keep this as an NFC Tools export-layer behavior. Do not modify the analyzer output rows to pretend the detections themselves lasted longer. The extra context exists to support review and upload preparation, especially eBird/Macaulay Library guidance to include ambient audio before the first target vocalization; Macaulay's audio-editing tutorials demonstrate keeping about 3 seconds of clean background before the first target sound when possible.

If BirdNET or Nighthawk output formats change, update `src/nfc_tools/clip_exporter.py` and `tests/test_clip_exporter.py` together. Tests should assert both the parsed analyzer intervals and the final ffmpeg `-ss`/`-t` values, including start/end-of-file clamping.

## Dashboard meter

The dashboard meter uses one visual mapping in both standby and recording states:

```text
input level -> dBFS -> percentage -> green/yellow/orange/red ramp
```

The browser applies each reading directly. It does not smooth between readings. The meter updates four times per second. During recording, readings come from the recording stream. In standby, the dashboard previews microphone input at the same visual refresh rate.

## CSV date and time convention

CSV files that report date and time should use separate columns:

```text
date,time
2026-06-13,16-11-31
```

Use `yyyy-mm-dd` for dates and 24-hour `hh-mm-ss` for times. Do not use combined timestamp strings such as `2026-06-13T15:00` in CSV output fields.

## eBird checklist exports

Completed scheduled recordings and the bulk-analysis importer write untested eBird Record Format Extended CSVs under `eBird checklists/` when an eBird state/province code is configured. Per-session names use `ebird_record_import_yyyy-mm-dd_hh-mm.csv` and `ebird_review_yyyy-mm-dd_hh-mm.csv`, based on the recording start time without seconds. Each night folder also gets `ebird_record_import_night_yyyy-mm-dd.csv` and `ebird_review_night_yyyy-mm-dd.csv`, combining all rows for that night so one eBird upload can create multiple checklists. Upload CSVs intentionally omit headers and UTF-8 byte-order marks to match the eBird Record Format sample; review CSVs include headers and a byte-order mark for spreadsheet applications. Its reference data and requirements live in [Nighthawk species codes, families, and eBird import guidance](docs/reference/nighthawk-species-family-lookup.md).

The September 11, 2026 reference pins Nighthawk commit `0f3dd63` and checks its 130 codes against eBird taxonomy 2025. The resulting entries cover 128 species and two slash taxa across 18 families. The separate Nighthawk family list contains 19 labels, including Corvidae. The combined lookup appends 19 family rows with `n/a` in **eBird code** and **Species**; these placeholders distinguish reference rows from species rows. Use the detailed family mapping table for actual accepted spuh codes and scope restrictions, including the five unresolved family mappings.

Preserve exact source codes and identification scope when implementing conversion. The reference lists five name or scope changes; in particular, `whimbr` and `yelwar` now resolve to slash taxa. Do not automatically select a successor species. Acoustic group labels such as `THSH` are outside the species/family lookup and require explicit group mappings; no runtime conversion currently consumes this document.

The eBird exporter uses accepted common names in the prescribed import fields, with no additional family column. Follow the eBird Record Format sample by leaving `Genus` and `Species` blank in generated upload rows. Write eBird upload CSVs as UTF-8 without a byte-order mark so row 1's common name has no leading invisible character; review CSVs may include a UTF-8 byte-order mark for spreadsheet compatibility. It keeps call totals in species comments (for example, `NFC 12`) rather than treating detections as individual-bird counts, keeps BirdNET detections separate, and adds weather to checklist comments without adding date/time text. Follow the reference's checklist metadata and import-format rules. The generated CSV is an untested direct-upload feature and still requires eBird's manual species and location matching steps.

When implementing checklist-level comments, follow the [civil twilight comment rules](docs/reference/nighthawk-species-family-lookup.md#civil-twilight-checklist-comments). At both civil dusk and civil dawn, a checklist ending at the boundary gets `Ending at civil twilight`; one starting at it gets `Starting at civil twilight`. Preserve other comments and avoid duplicate phrases. Determine this from the final checklist endpoints and the site's civil boundary times, not segment-period labels or detection times. Use the same boundary/timezone normalization as checklist splitting so recorder timing precision does not cause comments to disappear or attach to the wrong checklist.

Validate evening and morning boundaries on both sides, checklists with neither or both endpoints at civil boundaries, astronomical-only boundaries, existing comments, and repeated generation. Display annotations as separate lines, but join checklist comment data points with ` | ` in the eBird CSV checklist-comments field. eBird's required import layout and date/time formats take precedence over the general CSV convention above.

## Git and local generated files

The repository `.gitignore` covers local Python environments, caches, backups, patch scripts, raw test audio, logs, and diagnostic artifacts. Create `.venv` locally after cloning or downloading the repository; it is not part of the source tree.
