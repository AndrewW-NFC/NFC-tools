# NFC Tools

[![CI](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml)

NFC Tools is a local app for recording and analyzing nocturnal flight calls.

It can record overnight WAV files, run completed recordings through [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) and/or [Nighthawk](https://github.com/bmvandoren/Nighthawk), export review clips, and prepare eBird Record Format (Extended) CSVs from analyzer results.

NFC Tools runs on your computer. Your recordings stay on your device unless you choose to move or upload them elsewhere.

## Quick Start

NFC Tools does not yet have a one-click installer. For now, you need Git, Python 3.10 or newer, and a few Terminal or PowerShell commands.

If you use Git, start here.

macOS or Linux:

```bash
cd ~/Desktop
git clone https://github.com/AndrewW-NFC/NFC-tools.git nfc-tools
cd nfc-tools
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
nfc-tools
```

Windows PowerShell:

```powershell
cd $HOME\Desktop
git clone https://github.com/AndrewW-NFC/NFC-tools.git nfc-tools
cd nfc-tools
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
nfc-tools
```

The app opens in your browser at:

```text
http://127.0.0.1:8765/
```

If you download the GitHub ZIP instead of using Git, move the extracted folder somewhere convenient, such as your Desktop, then run the same setup commands from inside that folder. The ZIP folder is usually named `NFC-tools-main`. Use the folder name that exists on your computer.

## What You Need

* A computer that can stay on overnight.
* A microphone.
* Python 3.10 or newer.
* Enough disk space for overnight WAV files.
* Internet access for setup, maps, analyzer installation, and weather data.

After setup, NFC Tools can record and analyze saved audio without an internet connection if the needed analyzers are already installed.

## First Test

1. Open NFC Tools.
2. Go to **Settings**.
3. Set your recorder site name and coordinates.
4. Choose your microphone.
5. Use **Install / repair** if BirdNET or Nighthawk is not installed.
6. Return to **NFC Tools**.
7. Watch the meter to confirm microphone input.
8. Start a short test recording.
9. Check the dated output folder for `audio/`, `logs/`, `results/`, `clips/`, `eBird checklists/`, and `manifest.csv`.

A built-in microphone may work for a quick test, but it is not ideal for nocturnal flight call recording. An external USB microphone, audio interface, or purpose-built NFC microphone is a better field setup.

## What It Does

NFC Tools can:

* Record overnight audio in timed WAV segments, with clean breaks at midnight and NFC twilight boundaries.
* Run completed recordings through BirdNET, Nighthawk, or both.
* Optionally screen for possible wingbeats with the experimental wingbeat detector and flag candidates for review.
* Export short review clips from analyzer detections.
* Save each night in a dated folder on your Desktop or another location you choose.
* Show recording and analysis progress in a local browser dashboard.
* Check microphone input, storage, power status, analyzer setup, and weather logging before a recording.
* Import existing recordings, review inferred start times, correct recorder clock drift, convert files, analyze them, and resume interrupted work.
* Create eBird Record Format (Extended) CSVs and review CSVs from scheduled recordings or imported recordings.
* Create one combined nightly eBird upload CSV when a night contains more than one checklist.

NFC Tools does not confirm bird identifications, submit eBird checklists, or replace manual review. Analyzer results are suggestions. Review clips and CSVs are meant to make the review and upload process faster.

## Current Status

NFC Tools is early-stage software. It has been used successfully many times on macOS. Linux appears to work in an Ubuntu virtual machine but has not yet been used for real overnight recording. Windows passes automated tests but has not yet been tested in real-world use.

If you use Linux or Windows, expect setup details to need adjustment, especially around microphone selection, folder browsing, automatic scheduling, and packaged-app launch.

The eBird CSV feature is new. A generated file has imported successfully to eBird, but the workflow still needs broader real-world testing. Review generated files, imported species, and imported locations carefully.

## Main Pages

* **NFC Tools**: Start, stop, or schedule a recording session; watch the microphone meter; follow recording and analysis status.
* **Settings**: Set recorder site, map location, microphone, recording format, analyzers, power preferences, save location, and installation tools.
* **Readiness Check**: Run preflight checks for microphone input, storage, power, analyzer readiness, and environmental logging.
* **Import Recordings**: Bring existing recordings into the NFC Tools workflow, review start times, correct clock drift, convert files, analyze them, and prepare eBird CSVs.
* **Auto-record**: Enable or disable automatic nightly recording. This page is not yet tested.
* **Diagnostics**: Run health checks, make short test recordings, list devices, and download a diagnostics bundle for support.

The browser is only the control panel. The app and recordings are local.

## Recording Schedule

NFC Tools follows the timing structure of [eBird's Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC). The strict NFC counting window runs from astronomical dusk to astronomical dawn. Recordings should be split at midnight, and civil-to-astronomical twilight observations should be kept on separate checklists.

NFC Tools can use local twilight automatically or fixed clock times. Twilight schedules use the recorder site's coordinates and time zone. The **Astronomical twilight** preset records the strict NFC window. The **Civil twilight** preset records from civil dusk through civil dawn and labels the civil-to-astronomical periods separately.

The dashboard shows both the full recording window and the stricter NFC counting window. For testing, use **Record now even outside the scheduled window**.

## Power and Analysis

NFC Tools can prevent idle sleep while recording, or while recording and analyzing. It can also wait to analyze if the computer is on battery or below a battery threshold.

If analysis is waiting because of power settings, the dashboard shows **Start analysis now** when you can force analysis.

## Night Completeness and Recovery

Open **Night Summary** and choose a saved night. It shows the expected recording
window, recorded duration, gaps, unreadable or missing files, unfinished analysis,
and eBird export status. Recording coverage and analysis completion are reported
separately. Gaps longer than two seconds are listed; overlapping audio is counted
only once toward coverage. Older nights without a saved schedule show unknown
coverage. While recording is active, coverage is provisional.

After recording stops, choose **Resume unfinished work**. Recovery uses saved
progress to retry failed or interrupted analyzers and clip exports, retaining
completed analysis and rebuilding eBird exports without appending duplicate rows.
The saved progress survives an app restart. Older manifests retain successful
analysis; their clip exports are refreshed with stable filenames. Recovery uses
current Settings for unfinished work, so check the site and enabled analyzers
before resuming an older night. To intentionally rerun completed inference with
new settings, use `nfc analyze`.

Recovery waits until recording, analysis, and imports finish and honors the
analysis power policy. It cannot recreate missing audio or repair damaged WAVs;
restore missing files from a backup. The original audio is never modified.

## Output Folders

Each recording night is saved in a dated folder under your save location. The default save location is your Desktop:

```text
~/Desktop/2026-06-13/
```

A night folder can contain:

```text
audio/
results/
clips/
logs/
eBird checklists/
manifest.csv
```

The `audio/` folder holds WAV segments. Analyzer output stays in `results/<analyzer>/<recording-name>/`. Review clips go in `clips/<recording-start-HH-MM-SS>/`. Weather and environmental logs go in `logs/`. Review CSVs go in `review/` when eBird exports are off. When enabled, eBird upload and review CSVs go in `eBird checklists/`.

If a segment has no detections, NFC Tools does not create a `clips/` folder for that segment.

## File Names

Recorded WAV files include the segment order, protocol period, date, and start time:

```text
001_NFC_CIVIL_EVENING_2026-06-17_21-50-02.wav
002_NFC_2026-06-18_00-00-00.wav
003_NFC_CIVIL_MORNING_2026-06-18_02-52-11.wav
```

The three-digit number keeps files in order. `NFC_CIVIL_EVENING` is the evening civil-to-astronomical twilight period. `NFC` is the astronomical-dusk-to-astronomical-dawn count period. `NFC_CIVIL_MORNING` is the morning astronomical-to-civil twilight period.

Older NFC Tools filenames are still readable.

## Review Clips

NFC Tools exports review clips after analysis when detections are available. Clips are grouped by the recording segment's start time:

```text
clips/
  21-50-02/
    swathr (0.943)-Nighthawk.wav
    swathr (0.812)-BirdNET.wav
    WING (review required)-Wingbeats.wav
  00-00-00/
    sora (0.774)-BirdNET.wav
```

BirdNET and Nighthawk clip filenames follow the analyzer label:

```text
predicted_category (confidence)-Analyzer.wav
```

If two clips would have the same name, NFC Tools adds a number.

BirdNET clips come from BirdNET selection tables and use the minimum confidence set in Settings. The default is **0.500**; existing saved settings retain their configured value. Nighthawk clips come from Nighthawk Audacity labels. WING clips use `WING (review required)-Wingbeats.wav`, without a confidence value.

Clips include up to four seconds of context before and after the analyzer interval, bounded by the recording. This helps with review and follows the general Macaulay Library guidance to keep some ambient sound before the target vocalization when possible.

## eBird CSVs

Recording locations are independent of eBird. In Settings or Import Recordings, leave **Create eBird checklist files** off to use recording, analysis, clips, and review CSVs without eBird setup. Review CSVs then go in `review/`; enabled eBird exports retain their existing `eBird checklists/` filenames.

For a personal location, no location code is required: upload the CSV and select your existing location under **Fix Locations → Your Locations** in eBird. Personal locations are private and cannot be searched by NFC Tools.

For a public hotspot, select **Select a public hotspot** and search near your recording coordinates. Lookup requires an [eBird API key](https://ebird.org/data/download), entered for that search or supplied through `EBIRD_API_KEY`. The selected hotspot supplies its official export name and coordinates, without changing the recorder location. Still confirm the existing hotspot in eBird’s **Fix Locations** step; an ID or matching name in a CSV does not guarantee that eBird associates it with an existing location.

Scheduled recordings and imported recordings can write eBird Record Format (Extended) CSVs under `eBird checklists/` when optional eBird exports are enabled and country/state codes are configured.

Per-session files use:

```text
ebird_record_import_yyyy-mm-dd_hh-mm.csv
ebird_review_yyyy-mm-dd_hh-mm.csv
```

Each night folder can also contain combined nightly files:

```text
ebird_record_import_night_yyyy-mm-dd.csv
ebird_review_night_yyyy-mm-dd.csv
```

The combined upload file can contain more than one checklist. eBird separates checklist rows by the checklist fields in the upload, including date, start time, duration, location, and protocol.

Generated eBird upload rows use accepted common names in `Common Name` and leave `Genus` and `Species` blank, following the eBird Record Format sample. Species comments include NFC counts and broad call-type counts when available. BirdNET detections remain separate from NFC counts. Checklist comments include `Awaiting manual review` and weather conditions, but not date or time text.

The eBird upload CSV is written as UTF-8 without a byte-order mark so the first species name begins at the first byte. The companion review CSV includes a UTF-8 byte-order mark for spreadsheet applications.

WING candidates appear only in review CSVs, marked for manual review. They have no species assignment or confidence probability, do not contribute to NFC counts, and are excluded from eBird upload CSVs.

eBird still requires manual review after import. During eBird's Fix Locations step, choose the standard eBird hotspot when one exists rather than relying only on the free-text location name or coordinates.

## Import Existing Recordings

The **Import Recordings** page converts existing audio into a normal NFC Tools night folder and starts with BirdNET and Nighthawk selections from Settings, with Possible wingbeats checked by default. In step 1, select any combination of **BirdNET**, **Nighthawk**, and **Possible wingbeats**. At least one analyzer is required. This choice does not change Settings and is preserved when you pause and resume.

If validation reports an output-folder error, change that folder without re-entering session details or corrected recording times. NFC Tools checks the new destination and asks you to confirm storage again. Rescanning the same source also keeps corrections for unchanged files; new or modified files need timeline review. A failed recheck leaves your draft intact. Choosing a different source or explicitly planning another import starts a new file timeline.

The workflow is:

1. Choose analyzers for this import.
2. Choose a source folder and output folder.
3. Review session details and scan recordings.
4. Review start times, use **Correct recorder clock** if needed, and confirm the timeline.
5. Confirm the output and storage plan.
6. Start bulk processing and follow the run monitor.

Original recordings are never modified. Source and output folders must be different folders. NFC Tools supports common source formats such as AIFF, FLAC, M4A, MP3, OGG, and WAV, when ffmpeg can read them.

Processing converts audio to 48 kHz mono, 32-bit PCM WAV. It splits recordings at the configured segment length, twilight boundaries, midnight, and noon, which is the archive night-date boundary.

The run monitor shows the current recording, current analyzer, overall progress, and output folder. Progress advances as parts finish. **Pause after current part** finishes the current part before pausing. **Resume processing** continues from saved checkpoints in `<output>/.nfc-imports/`.

Imported recordings use the same output layout and review-clip rules as live recordings: `audio/`, `results/<analyzer>/<recording-name>/`, `clips/<HH-MM-SS>/`, `logs/`, `manifest.csv`, and `eBird checklists/`. WING results include CSV and Audacity label files under `results/wingbeats/`, with clips created when candidates are detected. Imports additionally store recovery and source metadata in `<output>/.nfc-imports/`.

If a paused or failed run is restored, you can resume it or use **Choose folder** to start a new plan. Selecting a folder leaves the earlier checkpoint intact; cancelling the chooser keeps the restored plan. Folder selection stays locked while processing is running.

Keep NFC Tools running while bulk processing is active. Missing analyzers may install on first use.

Environmental condition logs are written from the corrected recording time and import location when weather data is available. Past conditions come from Open-Meteo historical data. Missing conditions are reported in the CSV and job history.

Local times during the spring clock change that do not exist are rejected. For repeated times during the autumn clock change, choose the first or second occurrence in Session details. Elapsed recording duration remains accurate across clock changes.

## Analyzer Notes

[BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer) is an open-source acoustic analysis tool for identifying bird vocalizations. [Nighthawk](https://github.com/bmvandoren/Nighthawk) is a machine-learning model for detecting and classifying nocturnal flight calls in recordings from the Americas.

NFC Tools can install BirdNET and Nighthawk into managed local environments from Settings. During a recording session, NFC Tools runs the enabled analyzers, organizes the resulting files, and exports review clips when detections are available.

BirdNET results depend on site latitude and longitude. Keep the recorder site accurate before recording or analyzing.

Nighthawk output includes Raven selection tables and Audacity label files. BirdNET output includes CSV results and Raven-style selection tables. Original analyzer outputs remain in `results/`.

### Experimental wingbeat detection

**Possible wingbeats** is enabled by default for new configurations and checked by default in **Import Recordings → Analyzers**. You can turn it off there or in **Settings → Analyzers** for live recordings. Existing saved Settings selections are preserved. No separate model installation is needed.

The detector searches for repeated broadband pulses or repeating tones accompanied by softer, synchronized surrounding noise, including frequencies above 3 kHz, and labels candidate intervals `WING` for listening review. It does not identify a species or family. Its intervals are screening windows, not exact wingbeat start and stop times. Rhythmic rain, machinery, and rustling can trigger false positives, and quiet or irregular wingbeats may be missed. Field accuracy has not been established.

**This feature is still in development.** It has been tested on a small set of recordings covering a limited number of species: several ducks, mute swan, mourning dove, and double-crested cormorant, along with known false-positive recordings. These examples informed development and are not an independent validation set; performance across other species and recording conditions is not yet established. Please review every `WING` candidate manually.

## Weather Logs

The `logs/` folder includes environmental condition logs when weather data is available. `environmental_conditions.csv` is structured for spreadsheets. `environmental_conditions.txt` is a plain-text companion for copying conditions.

Each text line contains weather conditions separated by pipes:

```text
Temperature (F): 63.4° | Wind speed: 4.8 mph | Wind direction: 210° | 950 hPa wind speed: 11.2 mph | 950 hPa wind direction: 235° | Cloud cover: 18% | Precipitation: 0 mm
```

The generated eBird checklist comments keep the weather conditions and omit the date and time.

## Command-Line Helper

Most users can stay in the browser interface. The `nfc` helper is available for setup, diagnostics, and headless use:

| Command | What it does |
| --- | --- |
| `nfc doctor` | Runs health checks and reports missing tools, configuration problems, or setup issues. |
| `nfc devices` | Lists available audio input devices. |
| `nfc install-analyzers` | Installs or repairs both BirdNET and Nighthawk. |
| `nfc install-analyzers --only birdnet` | Installs or repairs only BirdNET. |
| `nfc install-analyzers --only nighthawk` | Installs or repairs only Nighthawk. |
| `nfc record` | Starts a recording session with saved settings. |
| `nfc record-once` | Runs one scheduled-style recording session and exits. |
| `nfc analyze /path/to/file.wav` | Analyzes one existing WAV file. |
| `nfc backfill 2026-05-10` | Reanalyzes all WAV files for a saved night folder. |
| `nfc autoschedule --enable` | Enables the nightly auto-recorder using the saved schedule. |
| `nfc autoschedule --disable` | Disables the nightly auto-recorder. |
| `nfc web` | Launches the local browser app. |

The `nfc-tools` command launches the local web app and opens the browser.

## Development

For development notes, see [README_DEV.md](README_DEV.md).

Questions, bug reports, and contributions are welcome through GitHub. Use [Issues](https://github.com/AndrewW-NFC/NFC-tools/issues) to report problems or ask questions, and [Pull Requests](https://github.com/AndrewW-NFC/NFC-tools/pulls) to suggest code or documentation changes.

## References

* [Nighthawk species codes, family mappings, and eBird import guidance](docs/reference/nighthawk-species-family-lookup.md)
* [eBird Guide to Protocols: Nocturnal Flight Call Count Protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC)
* [Macaulay Library Audacity tutorial](https://www.macaulaylibrary.org/resources/audio-editing-tutorials/editing-in-audacity/)
* [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/)
* NFC Discord community: the project maintainer is an admin. [Open a GitHub Issue](https://github.com/AndrewW-NFC/NFC-tools/issues) to ask for an invitation.
