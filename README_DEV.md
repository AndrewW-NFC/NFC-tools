# NFC Tools — Developer notes

These notes are for people modifying NFC Tools itself. For end-user instructions, see `README.md`.

NFC Tools is currently alpha software. The codebase includes support paths for macOS, Linux, and Windows, but recent hands-on testing has been strongest on macOS. Be cautious when changing code that touches microphones, native folder picking, automatic scheduling, analyzer installation, or browser permissions.

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

If Node.js is available, syntax-check the main browser scripts:

```bash
node --check src/nfc_tools/web/static/app.js
node --check src/nfc_tools/web/static/settings_page.js
```

Node.js is not required to run NFC Tools.

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

```bash
nfc doctor
nfc devices
nfc install-analyzers
nfc install-analyzers --only birdnet
nfc install-analyzers --only nighthawk
nfc record
nfc record-once
nfc analyze /path/to/file.wav
nfc backfill 2026-05-10
nfc export 2026-05-10 --min-conf 0.7 --out detections.csv
nfc export 2026-05-10 --ebird --min-conf 0.7 --out ebird.csv
nfc autoschedule --enable
nfc autoschedule --disable
nfc web
```

The `nfc-tools` command launches the web app and opens the browser.

## Repository map

Important files and directories:

```text
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
  Coordinates scheduled start, recording, stop, per-segment analysis, status updates, and manifest entries.

src/nfc_tools/recorder.py
  ffmpeg segment-mode recorder. Tracks completed WAV files and queues final partial files on stop.

src/nfc_tools/installer.py
  ffmpeg, BirdNET, and Nighthawk install/repair logic.

src/nfc_tools/analyzers/
  Built-in analyzer plugins and the analyzer registry.

src/nfc_tools/detections.py
  Parser layer that normalizes BirdNET and Nighthawk output into detection records.

src/nfc_tools/exporters.py
  Rich CSV export and eBird-style CSV export.

src/nfc_tools/autoschedule.py
  User-level OS scheduler support: launchd, systemd --user, and Windows Task Scheduler.

src/nfc_tools/doctor.py
  Health checks used by CLI and Diagnostics page.

src/nfc_tools/web/server.py
  FastAPI app factory and uvicorn launcher.

src/nfc_tools/web/routes.py
  Main web routes: wizard, dashboard, session control, Settings, install/repair, Diagnostics.

src/nfc_tools/web/routes_detections.py
  Detections browser, macOS folder picker, detection preview/browse routes, clip playback.

src/nfc_tools/web/routes_export.py
  CSV and eBird-style export download endpoints.

src/nfc_tools/web/routes_schedule.py
  Auto-record page routes.

src/nfc_tools/web/templates/
  Jinja templates for the local browser UI.

src/nfc_tools/web/static/
  Browser JavaScript and CSS.

tests/
  Unit tests for config, scheduling, filename parsing, detection parsing, and exporters.

tools/make_screenshots.py
  Documentation screenshot/mockup generator.
```

## Current web UI structure

The main navigation is defined in `src/nfc_tools/web/templates/base.html`.

Current nav order:

```text
NFC Tools
Settings
Detections
Auto-record
Diagnostics
```

Important templates:

```text
dashboard.html
  Main recording dashboard.

settings.html
  Site, map/location, microphone, sample rate, analyzer choices, and install/repair.

detections.html
  Detection-folder selection, preview, filters, summary, detection rows, and clip playback.

schedule.html
  Auto-record enable/disable page.

diagnostics.html
  Health checks and diagnostics-bundle download.

wizard.html
  First-run setup wizard.
```

Important static files:

```text
app.js
  Main dashboard behavior, mic meter, session start/stop, status rendering, install log handling.

settings_page.js
  Settings-page map/location behavior and layout enhancement.

settings_page.css
  Settings-page-specific map and layout CSS.

style.css
  General app layout and UI styling.
```

Avoid reintroducing the older experimental dashboard scripts:

```text
dashboard_live_status.js
dashboard_live_status.css
dashboard_status.js
dashboard_status.css
diagnostics_system.js
```

Recent work consolidated dashboard status/meter behavior into `app.js`.

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
  -> manifest.csv
  -> Detections page / CSV export
```

Key implementation points:

* `Session.start()` computes the relevant recording window.
* If the user schedules a future start, state becomes `awaiting_start`.
* If recording starts immediately, `Session._begin_recording()` creates the night folder and starts `Recorder`.
* `Recorder` runs ffmpeg in segment mode.
* When ffmpeg opens a new file, the previous segment is treated as complete.
* On manual or scheduled stop, the final partial WAV is also treated as complete if it exists and is non-empty.
* `Session._segment_done()` queues completed WAV files for analysis.
* `Session._analyze_one()` runs enabled analyzers and records results in `manifest.csv`.
* Analysis status is exposed through `/session/status` and `/ws/status`.

Dashboard status text should remain user-facing and plain-language. Avoid exposing raw filenames or developer-oriented messages in the main status area unless the user is in a diagnostic context.

Preferred public wording:

```text
Standing by for start of recording.
Recording…
Recording stopped. Analysis will begin soon.
Analyzing the recording.
BirdNET is analyzing the recording.
Nighthawk is analyzing the recording.
Analysis complete.
Recordings analyzed: 3 of 3.
Recordings left: 0.
```

Use official casing:

```text
BirdNET
Nighthawk
```

## Output folders

User-facing recording output goes to the Desktop:

```text
~/Desktop/YYYY-MM-DD/
  audio/
  results/
  logs/
  manifest.csv
```

Application config, logs, cache, and managed analyzer environments use platform-specific app directories through `platformdirs`.

Relevant helpers:

```text
paths.config_dir()
paths.data_dir()
paths.logs_dir()
paths.cache_dir()
paths.recordings_root()
paths.analyzers_root()
paths.night_dir(session_date)
```

## Configuration model

The config model lives in `src/nfc_tools/config.py`.

Current major sections:

```text
site
schedule
recording
analyzers
notifications
advanced
autoschedule
```

Current defaults include:

```text
site.name = "My site"
site.latitude = 42.415
site.longitude = -71.156
schedule.start_time = "21:00"
schedule.end_time = "06:15"
schedule.segment_minutes = 60
recording.sample_rate = 44100
recording.channels = 1
recording.bit_depth = 16
recording.filename_prefix = "NFC"
analyzers.enabled = ["birdnet", "nighthawk"]
analyzers.birdnet_min_conf = 0.25
advanced.web_host = "127.0.0.1"
advanced.web_port = 8765
```

The Settings page currently preserves schedule values as hidden fields, but it does not expose a visible schedule editor. The first-run wizard and existing config file remain the main places where schedule start/end values are set.

Known UI/documentation issue to watch: `schedule.html` currently tells users to change the time in Settings. That is no longer accurate if Settings does not expose visible schedule controls.

## Settings page

Current Settings page responsibilities:

* site name
* latitude
* longitude
* timezone
* map-selected location
* microphone
* sample rate
* enabled analyzers
* BirdNET minimum confidence
* install/repair controls for ffmpeg, BirdNET, and Nighthawk

The Settings map uses browser-side JavaScript and online map tiles. Do not make the map the only way to set location. Latitude, longitude, and timezone inputs must remain usable manually.

Current sample-rate options in the UI:

```text
44100
96000
```

## Detections page

The Detections page is implemented through `routes_detections.py`, `detections.html`, and `detections.py`.

It supports:

* folder selection
* previewing detection folders
* including subfolders
* filtering by confidence, analyzer, and species
* summary rows
* individual detection rows
* browser clip playback

The native folder picker currently uses macOS `osascript`. On non-macOS platforms, `/detections/pick-folder` returns a 501 response with a message that folder browsing is currently macOS-only in this local build.

Any cross-platform folder-picker improvement should preserve the rule that browser JavaScript cannot safely invent or access arbitrary local file paths without help from the local server.

## Analyzer installation

Analyzer installation lives in `installer.py`.

Current behavior:

* ffmpeg is installed through `imageio-ffmpeg` when using the install/repair control.
* BirdNET installs into a managed Python virtual environment.
* Nighthawk requires Python 3.10.
* If the app Python is not 3.10, Nighthawk installation can use a managed micromamba Python 3.10 environment.
* Broken or incomplete Nighthawk environments should not be reported as installed merely because a directory exists. The install/status logic should verify that `import nighthawk` works in the selected environment.

The Nighthawk installer intentionally prefers a valid managed Python 3.10 environment over a stale or incompatible venv.

## Analyzer plugin registry

The analyzer protocol lives in `src/nfc_tools/analyzers/base.py`.

A plugin is an object with:

```python
name: str

def run(wav_path: Path, output_dir: Path, cfg) -> AnalyzerResult:
    ...
```

Built-in analyzers self-register when imported.

Current built-ins:

```text
birdnet
nighthawk
```

Important: the registry exists, but there is not currently a dynamic loader that automatically imports arbitrary user plugin files from the data directory. To add a new built-in analyzer today, you need to:

1. Add a module under `src/nfc_tools/analyzers/`.
2. Register the plugin with `register(...)`.
3. Import the module in `src/nfc_tools/analyzers/__init__.py`.
4. Add installer/status support if the analyzer needs an external environment.
5. Add UI support if users should be able to enable it from Settings.
6. Add parser support in `detections.py` if its output should appear in Detections.
7. Add tests.

Do not document “drop a file into the data directory” plugin loading until such a loader exists.

## eBird-style export and NFC protocol caveat

The eBird-style exporter lives in `src/nfc_tools/exporters.py`.

Current behavior:

* `to_rich_csv()` exports normalized detection records.
* `to_ebird_csv()` groups detections by species and writes an eBird-style CSV.
* The current eBird-style export sets `Protocol` to `Stationary`.
* The export includes comments warning that detections are automated and require review.

Do not describe the current export as full eBird NFC protocol support.

For protocol-aware future work, treat these as separate tasks:

* decide whether exports should support eBird’s Nocturnal Flight Call Count protocol
* ensure duration, count, date, start time, location, effort, and comments match the actual observing effort
* avoid crossing midnight in ways that conflict with target protocol expectations
* distinguish automated detections from reviewed detections
* preserve enough evidence for review: WAV file, analyzer output, timestamp, confidence, and comments

Until that work is done, call the current export “eBird-style CSV” or “draft eBird import aid,” not “eBird submission” or “NFC protocol export.”

## Auto-record

Auto-record code is in `autoschedule.py` and `routes_schedule.py`.

Current OS-level backends:

```text
macOS: launchd
Linux: systemd --user
Windows: Task Scheduler
```

The scheduled task runs:

```bash
nfc record-once
```

Auto-record depends on the saved schedule start time. The computer must be awake, powered, and able to access the selected microphone when the OS scheduler launches the task.

Be conservative when changing this code. It is hard to test every operating system path from one machine.

## Diagnostics

Diagnostics code is split between:

```text
doctor.py
routes.py
diagnostics.html
```

Health checks currently cover:

* ffmpeg
* microphone availability
* internet/weather access
* enabled analyzer install status

The diagnostics bundle route includes available logs, config, and doctor output.

Do not include large WAV files, analyzer environments, cache directories, or recordings in diagnostics bundles.

## Testing

Run the test suite:

```bash
pytest -q
```

Run Python compilation:

```bash
python -m compileall src/nfc_tools
```

Optional JavaScript syntax checks, if Node.js is installed:

```bash
node --check src/nfc_tools/web/static/app.js
node --check src/nfc_tools/web/static/settings_page.js
```

Existing tests cover:

* config validation
* scheduler/date behavior
* ephemeris preset behavior
* filename parsing
* BirdNET and Nighthawk detection parsing
* CSV exporters

Before making recording or analyzer changes, also perform a live short recording test on at least one machine.

## Documentation screenshots

Generate HTML mockups:

```bash
python tools/make_screenshots.py
```

Generate PNG screenshots as well:

```bash
pip install playwright jinja2
playwright install chromium
python tools/make_screenshots.py --png
```

Screenshots are written under:

```text
docs/screenshots/
```

The screenshot generator uses fake data. It is useful for documentation layout, not for confirming runtime behavior.

## Building a desktop bundle

Briefcase configuration exists in `briefcase.toml`.

Experimental commands:

```bash
pip install briefcase
briefcase create
briefcase build
briefcase package
```

Treat packaging as experimental until a full release process has been tested on the target platform. Do not assume the Briefcase bundle is production-ready just because the config file exists.

## Release / commit checklist

Before pushing a meaningful change:

```bash
python -m compileall src/nfc_tools
pytest -q
```

If Node.js is installed:

```bash
node --check src/nfc_tools/web/static/app.js
node --check src/nfc_tools/web/static/settings_page.js
```

Also check:

```bash
git status
```

Do not commit:

```text
.venv/
__pycache__/
*.pyc
*.bak
Desktop recording folders
*.wav
managed analyzer environments
large downloaded model files
diagnostics bundles
```

For UI changes, manually check at least:

```text
/dashboard
/settings
/detections
/schedule
/diagnostics
```

For recording changes, do a short recording test and confirm:

* a WAV file is created
* the final partial WAV is queued after Stop
* enabled analyzers run or fail visibly
* `manifest.csv` is updated
* Detections can find the output folder

## Architecture principles

* Keep normal operation browser-based and local.
* Keep recordings on the user’s computer.
* Prefer plain-language UI over developer status messages.
* Do not expose full filenames in main dashboard status unless needed for diagnostics.
* Keep the microphone meter and recording/analysis status easy to understand.
* Treat analyzer detections as review leads, not confirmed records.
* Avoid overclaiming eBird/NFC protocol support.
* Be explicit about macOS-only or least-tested behavior.
* Keep setup and troubleshooting understandable for non-programmers.
* Preserve expert workflows without making beginners learn the internals first.
