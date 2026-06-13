# NFC Tools

NFC Tools is a local recording and review app for nocturnal flight call work.

It is designed for people who want to leave a computer and microphone running overnight, record audio in timed WAV segments, analyze completed segments, and review possible detections the next day.

NFC Tools runs on your own computer. Recordings stay on your device.

## Current status

NFC Tools is early-stage software. It is usable, but it should still be treated as alpha. Its code is AI-generated in ChatGPT and Claude, then tested against results produced by BirdNET and Nighthawk in their command-line environments. AI-assisted code generation and documentation have relied on defined review perspectives, including a Python programmer with experience structuring code for open source communities, a UX/UI designer, a high school science teacher, an ornithologist, and others.

The codebase includes support paths for macOS, Linux, and Windows. The current hands-on testing has been strongest on macOS. If you are using Linux or Windows, expect that some setup details may need adjustment, especially around audio-device selection, folder browsing, and automatic scheduling.

NFC Tools does not yet have a one-click installer. For now, installation requires Git, Python, and a few Terminal or PowerShell commands. After installation, normal use happens through the browser interface. You do not need to edit code to record, analyze, or review detections.

Automated detections are not confirmed bird records. They are leads for review. Listen to the audio before reporting detections, especially unusual species.

## What NFC Tools does

* Records overnight audio in timed WAV segments.
* Saves each night in a dated folder on your Desktop.
* Queues completed recording segments for analysis.
* Runs BirdNET and/or Nighthawk on recordings.
* Shows recording and analysis progress in a local browser dashboard.
* Provides a live microphone level meter while the dashboard is open.
* Provides a Settings page for recorder site, map location, microphone, recording format, analyzers, and install/repair tools.
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
* **Detections** — review possible detections after analysis.
* **Auto-record** — enable or disable automatic nightly recording.
* **Diagnostics** — check whether required tools, microphones, and analyzers are working.

The app is not uploading your recordings to a website. The browser is being used as the interface for a program running on your own computer.

## Recorder site and map location

The recorder site latitude and longitude are required for accurate BirdNET results and are also used for recording timestamps and weather logs.

On the Settings page, you can type latitude and longitude directly. Valid coordinates update the map pin. You can also use **Set to My Current Location** to set the map and coordinates from the device location reported by the browser.

## Microphone meter

The dashboard volume meter updates four times per second. It uses the same green-to-yellow-to-orange-to-red visual scale in standby and recording states, with no visual smoothing between readings. During recording, the meter follows the recording stream. In standby, the dashboard previews microphone input so the meter remains responsive before a session starts.

## Output folders and CSV date/time format

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

CSV files that report date and time use separate columns. Dates use `yyyy-mm-dd`; times use a 24-hour `hh-mm-ss` format. The app does not use combined timestamp strings such as `2026-06-13T15:00` in those CSV fields. The eBird-style export keeps the date and time formats required by eBird.

## Install from source

These steps are for someone who cloned or downloaded this repository and wants to run NFC Tools locally.

If words like “clone,” “repository,” or “virtual environment” are unfamiliar, that is normal. They are software setup terms, not birding terms. The important point is that this is the current installation method until NFC Tools has a one-click installer.

### A note about folder names and commands

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

### 1. Open a terminal

On macOS, open **Terminal**.

On Windows, open **PowerShell**.

On Linux, open your usual terminal app.

### 2. Get the NFC Tools files

#### Option A: Clone with Git

```bash
cd ~/Desktop
git clone https://github.com/AndrewW-NFC/NFC-tools.git nfc-tools
cd nfc-tools
```

#### Option B: Download the ZIP from GitHub

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

### 3. Create a Python virtual environment

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

### 4. Install NFC Tools

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

For development work and tests:

```bash
python -m pip install -e ".[dev]"
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

## Running NFC Tools after installation

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

## Running your first test

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

BirdNET and Nighthawk are external analyzer tools. NFC Tools calls them from the command line and organizes the resulting files.

BirdNET results depend on site latitude and longitude. Keep the recorder site accurate before recording or analyzing.

## Development

For development notes, see `README_DEV.md`.
