# NFC Tools

NFC Tools records overnight audio and helps you review possible nocturnal flight calls from migrating birds.

It is designed for people who want to leave a computer and microphone running overnight, then review bird-call detections the next day. It can record audio in timed WAV files, analyze each completed recording segment, show detections in a local browser interface, and export results for further review.

NFC Tools runs on your own computer. Audio stays on your device.

## What you need

- A Mac, Windows, or Linux computer that can stay on overnight.
- Python 3.10 or newer, if you are running from source.
- A microphone. A built-in mic is fine for testing, but an external USB mic or purpose-built NFC microphone is much better.
- Enough disk space for overnight WAV recordings. Plan on several GB per night, depending on sample rate, channels, and recording length.
- Internet access during setup, especially if installing analyzers.

## How to start the app from this repository

These steps are for someone who downloaded or cloned the repository and wants to run NFC Tools from source.

### 1. Open a terminal

On macOS, open **Terminal**.

On Windows, open **PowerShell**.

On Linux, open your usual terminal app.

### 2. Go to the NFC Tools folder

From the repository root, run:

```bash
cd software/nfc-tools
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

macOS or Linux:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

### 5. Start the app

Run:

```bash
nfc-tools
```

A browser window should open automatically.

If it does not, open this address in your browser:

```text
http://127.0.0.1:8765/
```

You can also start the local web app directly with:

```bash
nfc web
```

## First-run setup

The first time you open the app, it should take you to the setup wizard.

The wizard asks for:

1. **Your recording site**  
   Enter your town or coordinates so the app can label the site and calculate sun-based recording presets.

2. **Your microphone**  
   Choose an input device and test levels. If the app says the signal is too quiet, choose a different input, move the microphone, or adjust gain.

3. **Your recording schedule**  
   Choose start and end times. The default schedule is meant for overnight recording. You can also use sun-based presets.

4. **Analyzers**  
   Leave BirdNET and Nighthawk enabled unless you have a reason to use only one. The app can install analyzer support during setup.

After saving setup, the app opens the dashboard.

## Running your first test

Before trying a full overnight session, do a short test.

1. Start the app:

```bash
nfc-tools
```

2. Open the dashboard in your browser.

3. Confirm the health checks look reasonable.

4. Start a session.

5. Let it run long enough to create at least one audio segment.

6. Stop the session.

7. Open the results or detections page and confirm that audio files and analyzer output are being created.

## Running an overnight session

1. Plug in the computer.
2. Make sure sleep settings will not stop recording.
3. Connect and position the microphone.
4. Start NFC Tools:

```bash
nfc-tools
```

5. From the dashboard, start the session before the scheduled recording period.
6. Leave the computer on overnight.

NFC Tools records in segments. As each segment finishes, the app can begin analyzing it while the next segment records.

## Optional: automatic nightly recording

NFC Tools includes an autoschedule command for user-level scheduling.

Enable it:

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

NFC Tools stores configuration, logs, recordings, and analyzer results in user-specific application folders. The exact location depends on your operating system.

A typical night includes:

```text
recordings/
  YYYY-MM-DD/
    audio/
      NFC_YYYY-MM-DD_YYYY-MM-DD_HH-MM-SS.wav
    results/
      birdnet/
      nighthawk/
    manifest.csv
```

Use the app’s diagnostics page when you need help finding logs or creating a support bundle.

## Reviewing detections

After a session:

1. Open the app.
2. Go to the detections or results page.
3. Choose the night you want to review.
4. Filter by confidence, analyzer, or species.
5. Listen to clips before treating a detection as real.
6. Export a CSV only after review.

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

### The microphone is missing

Run:

```bash
nfc devices
```

Then reopen Settings and choose the correct input device.

On macOS, you may also need to grant microphone permission.

### The app says no microphone is configured

Open the web app and complete the setup wizard, or use Settings to choose a device.

### No detections appear

Check:

- Did the app create WAV files?
- Did analyzer installation finish?
- Does `nfc doctor` show any failures?
- Are the confidence filters set too high?
- Is the selected night correct?

### The computer stopped recording overnight

Check:

- Power cable
- Battery settings
- Sleep settings
- System updates
- Microphone connection
- Available disk space

## Privacy

NFC Tools is designed to run locally. Recordings stay on your computer. Network access may be used for setup tasks such as installing analyzers, looking up locations, downloading dependencies, or fetching optional weather data.

## Developer documentation

See `README_DEV.md` for contributor setup, test commands, architecture notes, and packaging commands.

## License

MIT. See `LICENSE`.
