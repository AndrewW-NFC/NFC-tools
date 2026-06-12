# NFC Tools

NFC Tools is a local recording and review app for nocturnal flight call work.

It is designed for people who want to leave a computer and microphone running overnight, record audio in timed WAV segments, analyze completed segments, and review possible detections the next day.

NFC Tools runs on your own computer. Recordings stay on your device.

## Current status

NFC Tools is early-stage software. It is usable, but it should still be treated as alpha. Its code is AI-generated in ChatGPT and Claude and matched against results produced by BirdNET and Nighthawk in their command line environments. AI code generation and documentation has relied on defined personas such as Python programmer with experience structuring code for open source communities, UX/UI designer, high school science teacher, ornithologist, and others.

The codebase includes support paths for macOS, Linux, and Windows. The current hands-on testing has been strongest on macOS. If you are using Linux or Windows, expect that some setup details may need adjustment, especially around audio-device selection, folder browsing, and automatic scheduling.

NFC Tools does not yet have a one-click installer. For now, installation requires Git, Python, and a few Terminal or PowerShell commands. After installation, normal use happens through the browser interface. You do not need to edit code to record, analyze, or review detections.

Automated detections are not confirmed bird records. They are leads for review. Listen to the audio before reporting detections, especially unusual species.

## Start here

If you are mainly a birder, recordist, teacher, student, or naturalist, start with these sections:

1. [What NFC Tools does](#what-nfc-tools-does)
2. [What you need](#what-you-need)
3. [What the app looks like](#what-the-app-looks-like)
4. [Running your first test](#running-your-first-test)
5. [Install from source](#install-from-source)

If you are a developer, see [Development](#development) and `README_DEV.md`.

## What NFC Tools does

* Records overnight audio in timed WAV segments.
* Saves each night in a dated folder on your Desktop.
* Queues completed recording segments for analysis.
* Runs BirdNET and/or Nighthawk on recordings.
* Shows recording and analysis progress in a local browser dashboard.
* Provides a live microphone level meter while the dashboard is open.
* Provides a Settings page for site, map/location, microphone, recording format, analyzers, and install/repair tools.
* Provides a Detections page for reviewing analyzer output.
* Provides an Auto-record page for enabling automatic nightly recording.
* Provides a Diagnostics page for health checks and support bundles.

## What NFC Tools does not do

NFC Tools does not confirm bird identifications for you.

It does not replace listening to the audio, checking date and location, comparing call types, or making a careful judgment before reporting a record.

It does not submit checklists to eBird. It can export detection data, including an eBird-style CSV, but that export should be treated as a draft or review aid.

## What you need

* A computer that can stay on overnight.
* Python 3.10 or newer.
* A microphone.
* Enough disk space for overnight WAV files.
* Internet access for setup tasks such as installing analyzers, loading map tiles, looking up locations, downloading dependencies, or fetching weather data.

A built-in microphone may work for a quick test, but it is not ideal for serious nocturnal flight call recording. An external USB microphone, audio interface, or purpose-built NFC microphone is more appropriate.

### Approximate file sizes

For mono 16-bit WAV audio:

* 44.1 kHz: about 318 MB per hour
* 96 kHz: about 691 MB per hour

Actual storage use depends on recording length, sample rate, channel count, and the number of nights saved.

## What the app looks like

NFC Tools opens in your browser, but it runs locally on your computer. The browser is the control panel for a local recording program.

The main pages are:

* **NFC Tools** — start, stop, or schedule a recording session; watch the microphone meter; follow recording and analysis status.
* **Settings** — set your site name, map location, microphone, recording format, and analyzers.
* **Detections** — review possible detections after analysis.
* **Auto-record** — enable or disable automatic nightly recording.
* **Diagnostics** — check whether required tools, microphones, and analyzers are working.

The app is not uploading your recordings to a website. The browser is being used as the interface for a program running on your own computer.

## Running your first test

Do a short test before trying a full overnight session.

1. Start NFC Tools.
2. Open the dashboard in your browser.
3. Confirm that the microphone meter is moving.
4. Confirm that Settings has the correct site, microphone, recording format, and analyzers.
5. Start a short recording session.
6. Let it run long enough to create at least one audio segment.
7. Stop the session.
8. Watch the Status area for analysis progress.
9. Open Detections and confirm that analyzer output was created.

A good first test is not about identifying birds. It is about confirming that your computer, browser, microphone, recorder, and analyzers are all working together.

## Install from source

These steps are for someone who cloned or downloaded this repository and wants to run NFC Tools locally.

If words like “clone,” “repository,” or “virtual environment” are unfamiliar, that is normal. They are software setup terms, not birding terms. The important point is that this is the current installation method until NFC Tools has a one-click installer.

### 1. Open a terminal

On macOS, open **Terminal**.

On Windows, open **PowerShell**.

On Linux, open your usual terminal app.

### 2. Clone the repository

```bash
git clone https://github.com/AndrewW-NFC/NFC-tools.git
cd NFC-tools
```

This downloads the NFC Tools source code and moves you into the project folder.

You should now be in the folder that contains:

```text
README.md
pyproject.toml
src/
```

### 3. Create a Python virtual environment

A virtual environment is a private Python workspace for this app.

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

Your prompt may now show `(.venv)`, which means the project’s private Python environment is active.

### 4. Install NFC Tools

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

### 5. Start the app

```bash
nfc-tools
```

The app starts a local web server and opens a browser window.

If the browser does not open automatically, go to:

```text
http://127.0.0.1:8765/
```

You can also start only the local web app with:

```bash
nfc web
```

## First run

On first run, NFC Tools may open a setup wizard. The wizard asks for:

1. Site name and location
2. Microphone
3. Recording time window
4. Analyzer choices

The wizard can look up a town or location using an online geocoding service. You can also enter latitude and longitude manually.

The wizard includes recording start and end times. The current Settings page does not expose a full schedule editor, so the first-run schedule values matter. Auto-record also uses the saved schedule.

## Main pages

### NFC Tools

The **NFC Tools** page is the main dashboard.

Use it to:

* schedule tonight’s recording session
* start recording immediately
* stop or cancel a session
* confirm the microphone meter is moving
* see active recording settings
* follow recording and analysis status

The microphone meter should run while the dashboard page is open. If it does not move, check browser microphone permission, the selected input device, and the microphone connection.

Typical status messages include:

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
BirdNET: successful
Nighthawk: successful
```

The dashboard summarizes analysis progress by count rather than by showing full WAV filenames.

### Settings

Use **Settings** for values that usually stay stable during a recording session:

* site name
* latitude
* longitude
* timezone
* map-selected location
* microphone
* recording sample rate
* enabled analyzers
* BirdNET minimum confidence
* install or repair buttons for ffmpeg, BirdNET, and Nighthawk

The map-selected location tool uses online map tiles. If the map does not load, you can still enter latitude, longitude, and timezone directly.

Current recording-format options in the Settings page are:

* 44.1 kHz
* 96 kHz

44.1 kHz is the normal default. 96 kHz creates much larger files but preserves higher frequencies if your microphone and audio interface support them.

### Detections

Use **Detections** to review analyzer output.

The Detections page can:

* choose a folder containing NFC Tools output
* preview detection folders
* include subfolders
* filter by confidence, analyzer, or species
* summarize detections by species
* show individual detections
* play audio clips in the browser

A valid NFC Tools detection folder usually contains:

```text
audio/
results/
```

The folder browser currently uses a native macOS folder picker in this local build. Linux and Windows path-selection behavior may need more testing or refinement.

### Auto-record

Use **Auto-record** to enable or disable automatic nightly recording.

Auto-record uses the saved recording start time. It installs a user-level operating-system scheduler task:

* macOS: launchd
* Linux: systemd user service/timer
* Windows: Task Scheduler

Your computer must be awake, powered, and able to access the selected microphone when the scheduled time arrives.

### Diagnostics

Use **Diagnostics** when something is not working.

Diagnostics runs health checks for:

* recording engine / ffmpeg
* microphone availability
* internet/weather access
* enabled analyzers

It can also create a diagnostics bundle containing logs and configuration information that can be shared with someone helping you troubleshoot.

## Running an overnight session

1. Plug in the computer.
2. Connect the microphone.
3. Start NFC Tools.
4. Open the dashboard.
5. Confirm that the microphone meter moves.
6. Confirm Settings are correct.
7. Start or schedule the recording session.
8. Leave the computer on and awake overnight.
9. Return later and review the Status area.
10. Open Detections to review possible calls.

NFC Tools records in segments. When a segment finishes, it can be queued for analysis while later audio continues recording.

Manual or scheduled stopping should also queue the final partial WAV file for analysis, as long as the file exists and is not empty.

## Output folders

NFC Tools stores recording nights on your Desktop.

A typical night folder looks like this:

```text
Desktop/
  YYYY-MM-DD/
    audio/
      NFC_YYYY-MM-DD_YYYY-MM-DD_HH-MM-SS.wav
    results/
      birdnet/
      nighthawk/
    logs/
    manifest.csv
```

The exact files depend on the session length, enabled analyzers, and whether analysis completed.

Application configuration, logs, cache files, and managed analyzer environments use platform-specific application folders.

## How to treat automated detections

BirdNET and Nighthawk detections are review leads, not confirmed records.

Before reporting a bird, especially an unusual species:

* listen to the audio
* compare the sound to known calls
* check whether the species is expected for date and location
* consider microphone noise, insects, aircraft, wind, and other false-positive sources
* keep the original WAV file and analyzer output together

NFC Tools helps organize the workflow. It does not replace expert review.

## NFC data and eBird

NFC Tools is designed around nocturnal flight call recording and review, but it does not currently submit observations to eBird.

The export command can create an eBird-style CSV. Treat that file as a draft for review, not as a completed checklist. The reviewer is responsible for deciding what, if anything, should be submitted.

Before using any exported detections for eBird or another database:

* verify the calls by listening
* remove false positives
* check dates, times, and location
* decide whether the effort should be reported as an NFC count or in another form
* make sure the protocol, duration, count, and comments match the actual observing effort

The current export is a convenience tool, not a guarantee of eBird protocol compliance.

## Student and beginner use

NFC Tools can be useful for students or beginning recordists because it makes the recording workflow visible:

* the microphone meter shows whether sound is reaching the computer
* the dashboard shows when recording is running
* the Status area shows whether analysis has started or finished
* the Detections page gives students material to review and question

A good first exercise is not an overnight session. Start with a short test recording, confirm that a WAV file was created, and then inspect the analyzer output.

Good beginner questions include:

* Did the microphone record sound?
* What sounds are visible or audible in the recording?
* Which detections look plausible?
* Which detections are likely false positives?
* What evidence would you need before reporting a bird?

## Analyzers

### BirdNET

BirdNET is a broad species classifier. NFC Tools can install BirdNET into a managed environment and run it on completed WAV segments.

BirdNET output should be reviewed by listening to the audio. Do not treat every automated row as a confirmed bird record.

### Nighthawk

Nighthawk is specialized for nocturnal flight call work. NFC Tools can install Nighthawk into a managed environment.

Nighthawk currently needs Python 3.10. If the app itself is running on a different Python version, NFC Tools may create a managed Python 3.10 environment using micromamba.

### Installing or repairing analyzers

Use the **Install / repair** section on Settings, or run:

```bash
nfc install-analyzers
```

You can install only one analyzer with:

```bash
nfc install-analyzers --only birdnet
nfc install-analyzers --only nighthawk
```

The first install can take several minutes.

## Command-line reference

NFC Tools is mainly designed around the local browser interface, but several command-line tools are available.

Run health checks:

```bash
nfc doctor
```

List audio input devices:

```bash
nfc devices
```

Install BirdNET and Nighthawk:

```bash
nfc install-analyzers
```

Start a recording session using saved settings:

```bash
nfc record
```

Run one synchronous recording session, used by Auto-record:

```bash
nfc record-once
```

Analyze one existing WAV file:

```bash
nfc analyze /path/to/file.wav
```

Reanalyze all WAV files for a night:

```bash
nfc backfill 2026-05-10
```

Export detections:

```bash
nfc export 2026-05-10 --min-conf 0.7 --out detections.csv
```

Export in eBird-style format:

```bash
nfc export 2026-05-10 --ebird --min-conf 0.7 --out ebird.csv
```

Enable automatic nightly recording:

```bash
nfc autoschedule --enable
```

Disable automatic nightly recording:

```bash
nfc autoschedule --disable
```

Launch the local web app:

```bash
nfc web
```

Launch the browser-opening app entry point:

```bash
nfc-tools
```

## Troubleshooting

### The app does not open

Start the web app directly:

```bash
nfc web
```

Then open:

```text
http://127.0.0.1:8765/
```

### The microphone meter does not move

Check:

* Did the browser ask for microphone permission?
* Did you allow microphone access?
* Is the microphone connected?
* Is the right input device selected in Settings?
* Does `nfc devices` list the microphone?
* Is another app already using the microphone?

### The app cannot find my microphone

Run:

```bash
nfc devices
```

Then choose the correct microphone in Settings.

On macOS, you may also need to grant microphone permission in System Settings.

### Analysis does not run

Check:

* Are BirdNET and/or Nighthawk enabled in Settings?
* Are the analyzers installed?
* Does Diagnostics report analyzer failures?
* Was a WAV file created?
* Is the WAV file non-empty?
* Is there enough disk space?

### The Detections page shows nothing

Check:

* Did analysis finish?
* Did the selected folder contain both `audio/` and `results/`?
* Is the confidence filter too high?
* Are you filtering by the wrong analyzer or species?
* Are the analyzer output files present under `results/birdnet/` or `results/nighthawk/`?

### The map does not load

The Settings map uses online map tiles. Check the internet connection.

You can still enter latitude, longitude, and timezone manually.

### Auto-record did not start

Check:

* Was Auto-record enabled?
* Was the computer awake?
* Was the computer plugged in?
* Was the selected microphone connected?
* Did the operating-system scheduler have permission to run user tasks?
* Does Diagnostics show any failures?

## Privacy and network use

NFC Tools is designed to run locally. Audio recordings stay on your computer.

Network access may be used for:

* installing Python packages and analyzer dependencies
* downloading micromamba, when needed for Nighthawk
* loading Settings map tiles
* looking up locations
* fetching weather data
* downloading or repairing analyzer environments

## Development

Developer notes are in `README_DEV.md`.

Useful development commands:

```bash
pip install -e ".[dev]"
pytest -q
uvicorn nfc_tools.web.server:create_app --reload --factory
```

## License

MIT. See `LICENSE`.
