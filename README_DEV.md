# NFC Tools — Developer notes

These notes are for people modifying NFC Tools itself. For end-user instructions, see `README.md`.

NFC Tools is currently alpha software. The codebase includes support paths for macOS, Linux, and Windows, but testing has been conducted thus far solely in macOS. Be cautious when changing code that touches microphones, native folder picking, automatic scheduling, analyzer installation, CSV output formats, environmental condition output formats, or browser permissions.

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
smoke tests on those operating systems before release claims should be strengthened.

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
  Coordinates scheduled start, recording, stop, per-segment analysis, status updates, session logging, weather logging, and manifest entries.

src/nfc_tools/session_logging.py
  CSV-backed dashboard/session log. CSV date and time fields are separate columns.

src/nfc_tools/weather.py
  Open-Meteo weather/environmental condition logging. Writes both spreadsheet-oriented CSV rows and paste-ready plain-text condition lines.

src/nfc_tools/recorder.py
  ffmpeg segment-mode recorder. Tracks completed WAV files and queues final partial files on stop.

src/nfc_tools/sounddevice_recorder.py
  sounddevice / PortAudio / CoreAudio recording backend, preferred on macOS.

src/nfc_tools/sounddevice_diagnostics.py
  sounddevice/CoreAudio diagnostic recording and level-measurement helpers.

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
  Main web routes: wizard, dashboard, session control, Settings, install/repair, Diagnostics.

src/nfc_tools/web/routes_schedule.py
  Auto-record page routes.

src/nfc_tools/web/templates/
  Jinja templates for the local browser UI.

src/nfc_tools/web/static/
  Browser JavaScript and CSS.

tests/
  Unit tests for config, scheduling, filename parsing, recording lifecycle, web routes, and power behavior.

tools/make_screenshots.py
  Documentation screenshot/mockup generator.
```

## Current web UI structure

The main navigation is defined in `src/nfc_tools/web/templates/base.html`.

Current nav order:

```text
NFC Tools
Settings
Recording Checklist
Auto-record
Diagnostics
```

Important templates:

```text
dashboard.html
  Main recording dashboard.

settings.html
  Recorder site, map/location, microphone, recording format, analyzer choices, and install/repair.

checklist.html
  Recording Checklist reference page.

schedule.html
  Auto-record enable/disable page. Not yet tested.

diagnostics.html
  Health checks and diagnostics-bundle download.

wizard.html
  First-run setup wizard.
```

Important static files:

```text
app.js
  Main dashboard behavior, meter, session start/stop, status rendering, install log handling.

settings_page.js
  Settings-page map/location behavior and layout enhancement.

settings_page.css
  Settings-page-specific map and layout CSS.

style.css
  General app layout and UI styling.
```

Avoid reintroducing older experimental dashboard scripts such as:

```text
dashboard_live_status.js
dashboard_live_status.css
dashboard_status.js
dashboard_status.css
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
```

On macOS, `recording.backend = auto` uses the sounddevice/CoreAudio path for normal recording. The ffmpeg/avfoundation path remains available as a fallback and diagnostic comparison path.

Recording segment boundaries are centralized in `src/nfc_tools/segments.py`. The astronomical twilight preset uses sun-altitude boundaries instead of fixed pre- or post-night buffers. A segment should stop at the earliest of the configured segment length, evening civil twilight, astronomical dusk, midnight, astronomical dawn, or morning civil twilight. Period labels are assigned from the segment start time with a small tolerance around NFC boundaries so recorder chunks near astronomical twilight still open the next file as `NFC_CIVIL_EVENING`, `NFC`, or `NFC_CIVIL_MORNING` as appropriate. Keep civil-to-astronomical twilight recordings separate from the strict astronomical-dusk-to-astronomical-dawn `NFC` period.

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

## Git and local generated files

The repository `.gitignore` covers local Python environments, caches, backups, patch scripts, raw test audio, logs, and diagnostic artifacts. Create `.venv` locally after cloning or downloading the repository; it is not part of the source tree.
