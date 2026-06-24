# NFC Tools

[![CI](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml)

NFC Tools is an app for recording and analyzing nocturnal flight call work.

It is designed for people who want to leave a computer and microphone running overnight, record audio in WAV segments, and run completed segments through [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) and/or [Nighthawk](https://github.com/bmvandoren/Nighthawk) to help identify bird vocalization.

NFC Tools runs on your own computer. Recordings stay on your device.

**Table of contents**

* [Current status](#current-status)
* [What NFC Tools does](#what-nfc-tools-does)
* [What NFC Tools does not do](#what-nfc-tools-does-not-do)
* [What you need](#what-you-need)
* [How to install and run](#how-to-install-and-run)
* [What the app looks like](#what-the-app-looks-like)
* [Recording schedule and power settings](#recording-schedule-and-power-settings)
* [Readiness and diagnostics](#readiness-and-diagnostics)
* [Recorder site and map location](#recorder-site-and-map-location)
* [The NFC protocol and file naming](#the-nfc-protocol-and-file-naming)
* [Importing existing recordings](#importing-existing-recordings)
* [Output folders](#output-folders)
* [Analyzer notes](#analyzer-notes)
* [Command-line helper](#command-line-helper)
* [Development](#development)
* [References](#references)

## Current status

NFC Tools is early-stage software. Its code is AI-generated in Codex, then tested against results produced by BirdNET and Nighthawk in their normal command-line environments. All efforts have been made to have the code be clean and follow structural best practices for developers who may want to extend it.

The codebase includes support paths for MacOS, Linux, and Windows. MacOS is the best-tested platform and has been used successfully many times. Linux appears to work in an Ubuntu virtual machine, but has not yet been used for real overnight recording. Windows passes automated tests, but has not yet been tested in real-world use. If you are using Linux or Windows, expect bugs and that some setup details may need adjustment, especially around audio-device selection, folder browsing, and automatic scheduling.

NFC Tools does not yet have a one-click installer. Maybe one day. For now, installation requires Git, Python, and a few Terminal or PowerShell commands. If you are new to words like "Git", "Python", and "PowerShell", that's okay. This guide tries to walk beginners through each step.

After installation, normal use happens your browser. You do not need to edit code to record or run analysis.

## What NFC Tools does

* Records overnight audio in timed WAV segments, with clean breaks at midnight and NFC twilight boundaries.
* Readies completed recording segments for analysis by BirdNET and/or Nighthawk.
* Exports short review clips from analyzer detections after successful analysis.
* Saves each night in a dated folder on your Desktop or another save location you choose.
* Shows recording and analysis progress in a local browser dashboard.
* Provides a live microphone level meter while the dashboard is open.
* Provides a Settings page for recorder location, microphone, recording format, schedule, power preferences, save location, analyzers, and install/repair tools.
* Provides a Readiness Check page for automated preflight checks before an overnight recording.
* Provides an Import Recordings planning page for choosing source/output folders and estimating storage for future bulk processing. This page is new and has not yet been tested with real bulk processing.
* Provides an Auto-record page for enabling automatic nightly recording. (Not yet tested)
* Provides a Diagnostics page for health checks and support bundles.

## What NFC Tools does not do

NFC Tools does not confirm BirdNET/Nighthawk's bird identifications for you. You should still review them yourself. Exported clips are a convenience for external review, not confirmed identifications.

It does not submit checklists to eBird or export eBird-ready detection summaries.

## What you need

* A computer that can stay on overnight.
* A microphone.
* Python 3.10 or newer.
* Enough disk space for overnight WAV files.
* Internet access for setup tasks such as installing analyzers, loading maps, and fetching weather data. An internet connection is not required for recording audio or analyzing saved recordings after the needed tools are installed.

A built-in microphone may work for a quick test, but it is not ideal for nocturnal flight call recording. An external USB microphone, audio interface, or purpose-built NFC microphone is more appropriate.

### WAV file sizes you can expect

For mono 16-bit WAV audio (common):

* 44.1 kHz: about 318 MB per hour
* 96 kHz: about 691 MB per hour

Actual storage use depends on recording length, sample rate, channel count, and the number of nights saved. 32-bit float audio uses more space than 16-bit audio.

## How to install and run

### Install from source

These steps are for someone who cloned or downloaded this repository and wants to run NFC Tools locally.

If words like “clone,” “repository,” or “virtual environment” are unfamiliar, that is okay. They are software setup terms, not birding terms. The important point is that this is the current installation method until NFC Tools has a one-click installer.

#### A note about folder names and commands

There are two different things with similar names:

* The **project folder** is the folder on your computer that contains the NFC Tools source files.
* The **app command** is the command you type to start NFC Tools after installation.

The app command is always:

```bash
nfc-tools
```

The command-line helper is always:

```bash
nfc
```

The project folder name depends on how you downloaded the code:

| How you got NFC Tools | Likely folder name |
| --- | --- |
| You used the `git clone` command shown below | `nfc-tools` |
| You downloaded the ZIP file from GitHub | `NFC-tools-main` |
| You renamed the folder yourself | whatever name you chose |

The folder name only matters for `cd`, which means “change directory.” Use the folder name that actually exists on your computer.

#### 1. Open a terminal

On macOS, open **Terminal**.

On Windows, open **PowerShell**.

On Linux, open your usual terminal app.

#### 2. Get the NFC Tools files

##### Option A: Clone with Git

```bash
cd ~/Desktop
git clone https://github.com/AndrewW-NFC/NFC-tools.git nfc-tools
cd nfc-tools
```

##### Option B: Download the ZIP from GitHub

If you download the ZIP from GitHub, the extracted folder will usually be named:

```text
NFC-tools-main
```

Move that folder somewhere convenient, such as your Desktop.

Then open Terminal or PowerShell and go into that folder.

macOS or Linux, if the folder is on your Desktop:

```bash
cd ~/Desktop/NFC-tools-main
```

Windows PowerShell, if the folder is on your Desktop:

```powershell
cd $HOME\Desktop\NFC-tools-main
```

After either Option A or Option B, you should be inside a folder that contains:

```text
README.md
pyproject.toml
src/
```

#### 3. Create a Python virtual environment

A virtual environment is a private Python workspace for this app. It is created locally on your computer after you download or clone the source code.

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

#### 4. Install NFC Tools

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

For development work and tests:

```bash
python -m pip install -e ".[dev]"
```

#### 5. Start the app

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

### Running NFC Tools after installation

You only need to install NFC Tools once. After that, each time you want to use it, open a command-line window, go back to the NFC Tools project folder, activate the virtual environment, and start the app.

macOS or Linux:

```bash
cd ~/Desktop/nfc-tools
source .venv/bin/activate
nfc-tools
```

Windows PowerShell:

```powershell
cd $HOME\Desktop\NFC-tools-main
.\.venv\Scripts\Activate.ps1
nfc-tools
```

### Running your first test

1. Open NFC Tools.
2. Go to **Settings**.
3. Set your recorder site name and coordinates.
4. Choose the microphone input device.
5. Use **Install / repair** if BirdNET or Nighthawk are not installed.
6. Return to **NFC Tools**.
7. Watch the meter to confirm that the app can see microphone input.
8. Start a short test recording.
9. Check the dated save-location folder for audio, logs, results, and any exported clips.

## What the app looks like

NFC Tools opens in your browser, but it runs locally on your computer. The browser is the control panel for a local recording program.

The main pages are:

* **NFC Tools** — start, stop, or schedule a recording session; watch the microphone meter; follow recording and analysis status.
* **Settings** — set recorder site name, latitude, longitude, map pin, microphone, recording format, and analyzers.
* **Readiness Check** — run automated checks for microphone input, storage, power, analyzer readiness, and environmental logging.
* **Import Recordings** — plan future processing for existing recordings. It can choose folders, scan supported audio files, and estimate output storage, but it does not start bulk analysis yet.
* **Auto-record** — enable or disable automatic nightly recording.
* **Diagnostics** — check whether required tools, microphones, and analyzers are working.

The app is not uploading your recordings to a website. The browser is being used as the interface for a program running on your own computer.

### Microphone meter

The dashboard volume meter updates four times per second. It uses the same green-to-yellow-to-orange-to-red visual scale in standby and recording states.

## Recording schedule and power settings

The dashboard shows both the full recording window and the stricter NFC counting window. You can schedule the next session normally, or choose **Record now even outside the scheduled window** for a manual test.

In Settings, the recording schedule can follow local twilight automatically or use fixed clock times. Twilight schedules use the recorder site's timezone and coordinates. Segment length is also set there; NFC Tools may shorten a segment when it needs to stop cleanly at midnight or an NFC twilight boundary.

NFC Tools can prevent idle sleep while recording, or while both recording and analyzing. The power settings also control whether analysis starts immediately after recording or waits when the computer is on battery or below a configured battery threshold. If analysis is deferred, the dashboard shows a **Start analysis now** button when it is safe for the user to force it.

## Readiness and diagnostics

The Readiness Check page runs preflight checks for microphone access, input signal, a short test recording, writable output folders, storage space, power status, analyzer installation, and environmental logging.

The Diagnostics page runs health checks, records short backend-specific test clips, lists ffmpeg/avfoundation devices, and can download a diagnostics bundle of logs and configuration for support.

## Recorder site and map location

The recorder site latitude and longitude are required for accurate BirdNET results and are also used for recording-time windows, file labels, and weather logs.

On the Settings page, you can type latitude and longitude directly. Valid coordinates update the map pin. You can also use **Set to My Current Location** to set the map and coordinates from the device location reported by the browser.

## The NFC protocol and file naming

NFC Tools follows the timing structure of [eBird's Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC). The strict NFC counting window runs from astronomical dusk to astronomical dawn, recordings should be split at midnight, and any observations from the civil-to-astronomical twilight periods should be kept on separate checklists.

To support that workflow, NFC Tools uses your selected location to calculate twilight windows from sun-altitude boundaries rather than fixed offsets from sunset or sunrise. The **Astronomical twilight** preset records the strict NFC window from astronomical dusk to astronomical dawn. The **Civil twilight** preset records from civil dusk through civil dawn and labels the civil-to-astronomical twilight periods as `NFC_CIVIL_EVENING` or `NFC_CIVIL_MORNING`.

The `audio/` folder contains WAV files named with the recording period:

```text
001_NFC_CIVIL_EVENING_2026-06-17_21-50-02.wav
002_NFC_2026-06-18_00-00-00.wav
003_NFC_CIVIL_MORNING_2026-06-18_02-52-11.wav
```

The three-digit number at the beginning is the recording segment order, so file browsers sort the recordings in sequence. `NFC_CIVIL_EVENING` is the evening civil-to-astronomical twilight period, `NFC` is the astronomical-dusk-to-astronomical-dawn NFC counting window, and `NFC_CIVIL_MORNING` is the morning astronomical-to-civil twilight period.

Older recordings without a segment number, or with both the session date and recording date in the filename, are still readable by the app. Future versions of NFC Tools hope to include a re-segmenting feature for old recordings that did not follow the NFC protocol's counting window.

## Importing existing recordings

The **Import Recordings** page is an early planning page for a future bulk-processing workflow. It is not yet tested with real bulk processing and does not start analysis yet.

The intended workflow is:

* Original recordings are never modified.
* The user chooses the source folder and output folder with native folder chooser buttons, not typed paths.
* NFC Tools scans supported audio files in the source folder.
* NFC Tools reads the selected output folder's free space.
* The page estimates processed audio, analyzer results, review clips, and total storage needs.
* Review clips are expected to be created automatically after analysis, using the same rules as normal one-night processing. Clip storage depends on how many detections the analyzers find, so this part is an estimate.

The future processing step should write a new NFC Tools-style archive in the selected output location, using the same night folders, `audio/`, `results/`, `clips/`, `logs/`, and `manifest.csv` structure as normal recording sessions. It should not copy full original source files as-is.

## Output folders

Each recording night is saved in a dated folder under your configured save location. By default, that save location is your Desktop:

```text
~/Desktop/2026-06-13/
```

Night folders can include:

```text
audio/
results/
clips/
logs/
manifest.csv
```

The `audio/` folder holds the original WAV recording segments. Analyzer output stays in the `results/` folder for use in BirdNET, Nighthawk, Raven, Audacity, or other external tools.

When analyzers find detections, NFC Tools also writes short review clips to `clips/`. Clips are grouped by the 24-hour start time of the recording segment that produced them:

```text
clips/
  21-50-02/
    swathr (0.943)-Nighthawk.wav
    swathr (0.812)-BirdNET.wav
  00-00-00/
    sora (0.774)-BirdNET.wav
```

Clip filenames follow Nighthawk-style label text: `predicted_category (confidence)-Analyzer.wav`. If two clips would have the same name in one start-time folder, NFC Tools adds a number, such as `swathr (0.943)-Nighthawk 2.wav`.

Nighthawk clips are exported from Nighthawk's Audacity labels. BirdNET clips are exported from BirdNET's selection table and only include detections at or above the BirdNET minimum confidence configured in Settings. NFC Tools does not add extra clip padding; it uses the begin and end times reported by the analyzer.

The `logs/` folder includes environmental condition logs when weather data is available. `environmental_conditions.csv` is structured for spreadsheets. `environmental_conditions.txt` is a plain-text companion file meant for copying a recording start's conditions into a text box. Each line contains the recording start date, recording start time, and environmental conditions, separated by pipes:

```text
Date: 2026-06-18 | Time: 02-52-11 | Temperature (F): 63.4° | Wind speed: 4.8 mph | Wind direction: 210° | 950 hPa wind speed: 11.2 mph | 950 hPa wind direction: 235° | Cloud cover: 18%
```

## Analyzer notes

[BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) is an open-source acoustic analysis tool for identifying bird vocalizations in audio recordings. [Nighthawk](https://github.com/bmvandoren/Nighthawk) is a machine-learning model for detecting and classifying nocturnal flight calls in recordings from the Americas.

NFC Tools can install BirdNET and Nighthawk into managed local environments from the Settings page. During a recording session, NFC Tools calls the enabled analyzers from the command line, organizes the resulting files, and exports review clips when detections are available.

BirdNET results depend on site latitude and longitude. Keep the recorder site accurate before recording or analyzing.

Nighthawk output includes Raven selection tables and Audacity label files. BirdNET output includes CSV results and Raven-style selection tables. The original analyzer outputs remain in `results/` even when clips are exported.

## Command-line helper

Most users can stay in the browser interface. The `nfc` helper is available for setup, diagnostics, and headless use:

| Command | What it does |
| --- | --- |
| `nfc doctor` | Runs health checks and reports missing tools, configuration problems, or setup issues. |
| `nfc devices` | Lists available audio input devices so you can identify microphone names and device IDs. |
| `nfc install-analyzers` | Installs or repairs both BirdNET and Nighthawk in NFC Tools-managed local environments. |
| `nfc install-analyzers --only birdnet` | Installs or repairs only the BirdNET environment. |
| `nfc install-analyzers --only nighthawk` | Installs or repairs only the Nighthawk environment. |
| `nfc record` | Starts a recording session immediately using saved settings, then runs until the configured end time or until you stop it. |
| `nfc record-once` | Runs one scheduled-style recording session and exits; this is mainly used by automatic scheduling. |
| `nfc analyze /path/to/file.wav` | Analyzes one existing WAV file using the saved analyzer settings. |
| `nfc backfill 2026-05-10` | Reanalyzes all WAV files for a saved night folder by date. |
| `nfc autoschedule --enable` | Installs or enables the nightly auto-recorder using the saved schedule. |
| `nfc autoschedule --disable` | Removes or disables the nightly auto-recorder. |
| `nfc web` | Launches the local browser app. |

The `nfc-tools` command launches the local web app and opens the browser.

## Development

For development notes, see `README_DEV.md`.

Questions, bug reports, and contributions are welcome through GitHub. You can use [Issues](https://github.com/AndrewW-NFC/NFC-tools/issues) to report problems or ask questions, and [Pull Requests](https://github.com/AndrewW-NFC/NFC-tools/pulls) to suggest code or documentation changes.

## References

* [eBird Guide to Protocols: Nocturnal Flight Call Count Protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC)
* [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/)
* NFC Discord community: the project maintainer is an admin. [Open a GitHub Issue](https://github.com/AndrewW-NFC/NFC-tools/issues) to ask for an invitation.
