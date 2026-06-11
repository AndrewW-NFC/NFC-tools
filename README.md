This is a junk draft of a READAME so far. It shouldn't yet be relied upon.

# NFC Tools

NFC Tools records overnight audio for nocturnal flight call work and helps you review possible detections from migrating birds.

It is designed for people who want to leave a computer and microphone running overnight, save audio in timed WAV segments, analyze each completed segment, and review likely detections the next day. NFC Tools runs on your own computer. Audio stays on your device.

## What NFC Tools does

* Records overnight audio in timed WAV segments.
* Saves each night in a dated folder on your Desktop.
* Can analyze completed recording segments while later segments continue recording.
* Supports BirdNET and Nighthawk analysis.
* Shows recording and analysis progress in a local browser dashboard.
* Provides a Settings page for site, microphone, recording format, and analyzer setup.
* Provides a Detections page for reviewing analyzer output.
* Provides Auto-record and Diagnostics pages for scheduling and troubleshooting.

## What you need

* A Mac, Windows, or Linux computer that can stay on overnight.
* Python 3.10 or newer, if you are running from source.
* A microphone. A built-in mic is fine for testing, but an external USB microphone or purpose-built NFC microphone is much better.
* Enough disk space for overnight WAV recordings. At 44.1 kHz, mono, 16-bit audio, plan on roughly 318 MB per hour. At 96 kHz, mono, 16-bit audio, plan on roughly 691 MB per hour.
* Internet access during setup, especially for installing analyzers, loading map tiles, looking up locations, or fetching optional weather data.

## Install and start from source

These steps are for someone who cloned or downloaded this repository and wants to run NFC Tools locally.

### 1. Open a terminal

On macOS, open **Terminal**. On Windows, open **PowerShell**. On Linux, open your usual terminal app.

### 2. Clone the repository

```bash
git clone https://github.com/AndrewW-NFC/NFC-tools.git
cd NFC-tools
```

You should now be in the folder that contains `pyproject.toml`, `README.md`, and the `src/` folder.

### 3. Create a Python virtual environment

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

macOS, Linux, or Windows PowerShell:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

### 5. Start the app

```bash
nfc-tools
```

A browser window should open automatically. If it does not, open:

```text
http://127.0.0.1:8765/
```

You can also start the local web app directly with:

```bash
nfc web
```

## Main pages

### NFC Tools dashboard

The dashboard is the main recording page.

Use it to:

* start a scheduled recording session
* start recording immediately when needed
* stop or cancel a session
* watch the live microphone meter
* see plain-language recording and analysis status

The volume meter is intended to run whenever the dashboard page is open. If the meter does not move, check browser microphone permission, the selected input device, and the microphone connection.

Dashboard status messages use plain language, such as:

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

The dashboard does not need to show full WAV filenames during normal use. It summarizes progress by counting recordings analyzed and recordings left.

### Settings

Use Settings for setup values that usually do not change during a recording session:

* site name
* latitude and longitude
* timezone
* map-selected location
* microphone
* recording format
* enabled analyzers
* analyzer installation or repair

The map-selected location control uses online map tiles, so it needs an internet connection to display the map. Latitude, longitude, and timezone fields remain available even if the map does not load.

Scheduling controls are not part of Settings. Use the dashboard and Auto-record page for recording sessions and scheduling workflows.

### Detections

Use Detections to review analyzer output after recording. Automated detections are leads, not proof. Listen to the audio before treating a detection as real, and especially before reporting unusual birds.

### Auto-record

Use Auto-record for automatic nightly recording setup. Keep the computer awake and plugged in. Autoscheduling cannot record if the computer is shut down, asleep, or missing the selected microphone.

### Diagnostics

Use Diagnostics when something is not working. It is the place to look for system checks, logs, and troubleshooting information.

## Running your first test

Before trying a full overnight session, do a short test.

1. Start the app:

   ```bash
   nfc-tools
   ```

2. Open the dashboard in your browser.

3. Confirm that the microphone meter is moving.

4. Confirm that Settings has the correct site, microphone, recording format, and analyzers.

5. Start a session.

6. Let it run long enough to create at least one audio segment.

7. Stop the session.

8. Watch the dashboard Status area for analysis progress.

9. Open Detections and confirm that analyzer output was created.

## Running an overnight session

1. Plug in the computer.

2. Make sure sleep settings will not stop recording.

3. Connect and position the microphone.

4. Start NFC Tools:

   ```bash
   nfc-tools
   ```

5. Check the dashboard microphone meter.

6. Start or schedule the recording session before the intended recording period.

7. Leave the computer on overnight.

NFC Tools records in segments. As each segment finishes, the app can begin analyzing it while the next segment records.

## Optional: automatic nightly recording

Enable automatic recording:

```bash
nfc autoschedule --enable
```

Disable it:

```bash
nfc autoschedule --disable
```

Keep the computer awake and plugged in. Autoscheduling cannot record if the computer is shut down, asleep, or missing the selected microphone.

## Useful command-line checks

List available microphones:

```bash
nfc devices
```

Run health checks:

```bash
nfc doctor
```

Install analyzers:

```bash
nfc install-analyzers
```

Record using saved settings:

```bash
nfc record
```

Analyze one existing WAV file:

```bash
nfc analyze /path/to/file.wav
```

Reanalyze a whole night:

```bash
nfc backfill 2026-05-10
```

Export detections:

```bash
nfc export 2026-05-10 --ebird --min-conf 0.7 --out detections.csv
```

## Where output goes

NFC Tools stores nightly recordings on your Desktop in dated folders. A typical night looks like this:

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

The exact contents depend on which analyzers are enabled and whether analysis has finished.

Use the app’s Diagnostics page when you need help finding logs or checking whether required tools are installed.

## Analyzer notes

### BirdNET

BirdNET can be enabled in Settings. It analyzes audio and produces candidate species detections.

BirdNET results are useful for screening audio, but they should not be treated as confirmed records without listening.

### Nighthawk

Nighthawk can also be enabled in Settings. It may use a managed Python 3.10 environment if the app needs one for compatibility.

If Nighthawk is not available, use Settings or Diagnostics to install or repair analyzer support.

## Reviewing detections

After a session:

1. Open the app.
2. Go to Detections.
3. Choose the folder or night you want to review.
4. Filter or sort detections as needed.
5. Listen to audio before treating a detection as real.
6. Export results only after review.

Automated detections are leads, not proof. Listen to the audio before reporting unusual birds.

## Troubleshooting

### The app does not open in my browser

Start it manually:

```bash
nfc web
```

Then open:

```text
http://127.0.0.1:8765/
```

### The microphone meter is not moving

Check:

* Did the browser ask for microphone permission?
* Is the correct microphone selected in Settings?
* Is the microphone connected?
* Is another app using the microphone?
* Does `nfc devices` show the microphone?

### The microphone is missing

Run:

```bash
nfc devices
```

Then reopen Settings and choose the correct input device. On macOS, you may also need to grant microphone permission.

### No detections appear

Check:

* Did the app create WAV files?
* Did analyzer installation finish?
* Are BirdNET and/or Nighthawk enabled?
* Does Diagnostics show any failures?
* Are the confidence filters set too high?
* Is the selected night or folder correct?

### The computer stopped recording overnight

Check:

* power cable
* battery settings
* sleep settings
* system updates
* microphone connection
* available disk space

### The map does not appear in Settings

The map uses online map tiles. If the map does not load, check the internet connection. You can still enter latitude and longitude directly.

## Privacy

NFC Tools is designed to run locally. Recordings stay on your computer.

Network access may be used for setup tasks such as installing analyzers, looking up locations, downloading dependencies, loading map tiles, or fetching optional weather data.

## Developer documentation

See `README_DEV.md` for contributor setup, test commands, architecture notes, and packaging commands.

## License

MIT. See `LICENSE`.
