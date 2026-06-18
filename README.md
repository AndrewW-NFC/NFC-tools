# NFC Tools

NFC Tools is a local recording and analyzer-handoff app for nocturnal flight call work.

It is designed for people who want to leave a computer and microphone running overnight, record audio in timed WAV segments, and hand completed segments to [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) and/or [Nighthawk](https://github.com/bmvandoren/Nighthawk).

NFC Tools runs on your own computer. Recordings stay on your device.

## Current status

NFC Tools is early-stage software. It is usable, but it should still be treated as alpha. Its code is AI-generated in ChatGPT and Claude, then tested against results produced by BirdNET and Nighthawk in their command-line environments.

The codebase includes support paths for macOS, Linux, and Windows. Testing has been conducted thus far solely in macOS. If you are using Linux or Windows, expect that some setup details may need adjustment, especially around audio-device selection, folder browsing, and automatic scheduling.

NFC Tools does not yet have a one-click installer. For now, installation requires Git, Python, and a few Terminal or PowerShell commands. After installation, normal use happens through the browser interface. You do not need to edit code to record or run analyzer handoff.

NFC Tools does not provide a call-review workflow. Review, interpretation, and reporting remain in BirdNET, Nighthawk, and your usual external tools.

## What NFC Tools does

* Records overnight audio in timed WAV segments, with clean breaks at midnight and NFC twilight boundaries.
* Saves each night in a dated folder on your Desktop.
* Queues completed recording segments for analysis.
* Runs BirdNET and/or Nighthawk on recordings.
* Provides a Recording Checklist for your reference before recording.
* Shows recording and analysis progress in a local browser dashboard.
* Provides a live microphone level meter while the dashboard is open.
* Provides a Settings page for recorder site, map location, microphone, recording format, analyzers, and install/repair tools.
* Provides an Auto-record page for enabling automatic nightly recording.
* Provides a Diagnostics page for health checks and support bundles.

## What NFC Tools does not do

NFC Tools does not confirm bird identifications for you.

It does not review calls, compare call types, annotate detections, or make a judgment before reporting a record.

It does not submit checklists to eBird or export eBird-ready detection summaries.

## What you need

* A computer that can stay on overnight.
* Python 3.10 or newer.
* A microphone.
* Enough disk space for overnight WAV files.
* Internet access for setup tasks such as installing analyzers, loading map tiles, looking up locations, downloading dependencies, or fetching weather data.

A built-in microphone may work for a quick test, but it is not ideal for serious nocturnal flight call recording. An external USB microphone, audio interface, or purpose-built NFC microphone is more appropriate.

### Approximate WAV file sizes

For mono 16-bit WAV audio:

* 44.1 kHz: about 318 MB per hour
* 96 kHz: about 691 MB per hour

Actual storage use depends on recording length, sample rate, channel count, and the number of nights saved. 32-bit float audio uses more space than 16-bit audio.

## What the app looks like

NFC Tools opens in your browser, but it runs locally on your computer. The browser is the control panel for a local recording program.

The main pages are:

* **NFC Tools** — start, stop, or schedule a recording session; watch the microphone meter; follow recording and analysis status.
* **Settings** — set recorder site name, latitude, longitude, map pin, microphone, recording format, and analyzers.
* **Recording Checklist** — check the microphone, meter, time window, storage, and analyzer setup before recording.
* **Auto-record** — enable or disable automatic nightly recording.
* **Diagnostics** — check whether required tools, microphones, and analyzers are working.

The app is not uploading your recordings to a website. The browser is being used as the interface for a program running on your own computer.

## Recorder site and map location

The recorder site latitude and longitude are required for accurate BirdNET results and are also used for recording windows, file labels, and weather logs.

On the Settings page, you can type latitude and longitude directly. Valid coordinates update the map pin. You can also use **Set to My Current Location** to set the map and coordinates from the device location reported by the browser.

## The NFC protocol and file naming

NFC Tools follows the timing structure of [eBird's Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC). The strict NFC counting window runs from astronomical dusk to astronomical dawn, recordings should be split at midnight, and any observations from the civil-to-astronomical twilight periods should be kept on separate checklists.

To support that workflow, NFC Tools uses your selected location to automatically start and stop recordings at your site's civil dusk, then astronomical dusk, then midnight, then astronomical dawn, and finally civil dawn. That's in addition to any stops that hit the hour-long limit.

The astronomical twilight preset uses sun-altitude boundaries rather than fixed offsets from sunset or sunrise. When you use that preset, NFC Tools records from civil dusk through civil dawn and labels the civil-to-astronomical twilight periods as `NFC_CIVIL_EVENING` or `NFC_CIVIL_MORNING`.

The `audio/` folder contains WAV files named with the recording period:

```text
NFC_CIVIL_EVENING_2026-06-17_2026-06-17_21-50-02.wav
NFC_2026-06-17_2026-06-18_00-00-00.wav
NFC_CIVIL_MORNING_2026-06-17_2026-06-18_02-52-11.wav
```

`NFC_CIVIL_EVENING` is the evening civil-to-astronomical twilight period, `NFC` is the astronomical-dusk-to-astronomical-dawn NFC counting window, and `NFC_CIVIL_MORNING` is the morning astronomical-to-civil twilight period.

## Microphone meter

The dashboard volume meter updates four times per second. It uses the same green-to-yellow-to-orange-to-red visual scale in standby and recording states, with no visual smoothing between readings. During recording, the meter follows the recording stream. In standby, the dashboard previews microphone input so the meter remains responsive before a session starts.

## Output folders

Each recording night is saved in a dated folder on your Desktop, for example:

```text
~/Desktop/2026-06-13/
```

Typical contents include:

```text
audio/
results/
logs/
manifest.csv
```

Analyzer output stays in the `results/` folder for use in BirdNET, Nighthawk, or other external review tools.

The `logs/` folder includes environmental condition logs when weather data is available. `environmental_conditions.csv` is structured for spreadsheets. `environmental_conditions.txt` is a plain-text companion file meant for copying an hour's conditions into a text box. Each line contains environmental conditions only, separated by pipes:

```text
Temperature (F): 63.4° | Wind speed: 4.8 mph | Wind direction: 210° | 950 hPa wind speed: 11.2 mph | 950 hPa wind direction: 235° | Cloud cover: 18%
```

## How to install and run

### Install from source

These steps are for someone who cloned or downloaded this repository and wants to run NFC Tools locally.

If words like “clone,” “repository,” or “virtual environment” are unfamiliar, that is normal. They are software setup terms, not birding terms. The important point is that this is the current installation method until NFC Tools has a one-click installer.

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
9. Check the dated Desktop folder for audio, logs, and results.

## Analyzer notes

[BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) is an open-source acoustic analysis tool for identifying bird vocalizations in audio recordings. [Nighthawk](https://github.com/bmvandoren/Nighthawk) is a machine-learning model for detecting and classifying nocturnal flight calls in recordings from the Americas.

NFC Tools can install BirdNET and Nighthawk into managed local environments from the Settings page. During a recording session, NFC Tools calls the enabled analyzers from the command line and organizes the resulting files.

BirdNET results depend on site latitude and longitude. Keep the recorder site accurate before recording or analyzing.

## Development

For development notes, see `README_DEV.md`.

## References

* [eBird Guide to Protocols: Nocturnal Flight Call Count Protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC)
* [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/)
* NFC Discord community: the project maintainer is an admin. [Open a GitHub Issue](https://github.com/AndrewW-NFC/NFC-tools/issues) to ask for an invitation.
