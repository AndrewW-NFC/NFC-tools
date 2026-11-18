# NFC Tools 0.8.3

For file and folder responsibilities, see the [codebase guide](CODEBASE.md).

> BirdNET upgrade: see [what changes and how to return to the previous version](docs/birdnet-3-upgrade.md).

[![CI](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml)

NFC Tools records and analyzes nocturnal flight calls on your computer. It uses [Nighthawk](https://github.com/bmvandoren/Nighthawk) and [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer), creates audio clips for review, and prepares optional eBird bulk-upload files. It also includes an experimental wingbeat detector.

The app opens in your browser. Recording and analysis run on your computer. Recording and analysis can run offline after NFC Tools and the analyzers are installed. Internet access is needed for initial setup and optional features such as maps and weather data.

NFC Tools has been used smoothly for thousands of recordings on macOS. Linux has been tested in an Ubuntu virtual machine, but not yet for real overnight recording. Windows passes automated tests and one real-world report of it running smoothly, but I would welcome more reports about whether NFC Tools runs as expected on your Windows machine.

NFC Tools uses a pinned BirdNET Analyzer 3.0 build with the BirdNET 3.0 model (developer preview 3.1). The previous BirdNET 2.4 installation is retained separately. Confidence scores differ between models; use fresh output folders when comparing results.

## Previous version

The [`nfc-tools-previous/`](nfc-tools-previous/SNAPSHOT.md) folder contains the
pre-upgrade 0.8.2 source using BirdNET 2.4. It is a source snapshot, not a second
installed app. See its instructions for running it in a separate environment.
The main app does not load code from that folder.

## Getting started

You need Python 3.10 or newer, Git, a command-line application such as Terminal on macOS or PowerShell on Windows, and a microphone. For overnight recording, you also need enough storage for WAV files and a computer that stays awake. Internet access is needed for initial installation of NFC Tools and the analyzers.

### Installation on macOS or Linux

Open your command-line tool and enter/paste this:

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

#### Running after installation on macOS or Linux

Try `nfc-tools` first. If your terminal already recognizes the command (for example, your installation is on PATH or its environment is already active), that is all you need.

If you get “command not found” after following the installation above, run this single command; activating the virtual environment is optional:

```bash
~/Desktop/nfc-tools/.venv/bin/nfc-tools
```

Alternatively, activate the environment and use the short command:

```bash
cd ~/Desktop/nfc-tools
source .venv/bin/activate
nfc-tools
```

### Installation on Windows

Open PowerShell and enter this:

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

#### Running after installation on Windows

Try `nfc-tools` first. If PowerShell already recognizes the command, that is all you need.

Otherwise, after following the installation above, run this single command; activating the virtual environment is optional:

```powershell
& "$HOME\Desktop\nfc-tools\.venv\Scripts\nfc-tools.exe"
```

Alternatively, activate the environment and use the short command:

```powershell
cd $HOME\Desktop\nfc-tools
.\.venv\Scripts\Activate.ps1
nfc-tools
```

These commands assume you installed NFC Tools in the `nfc-tools` folder on your Desktop. If you chose another location, adjust the path in the launch or `cd` command. Keep the terminal open while NFC Tools runs; press Ctrl+C to stop it.

The app opens at [http://127.0.0.1:8765/](http://127.0.0.1:8765/).

### Analyzer setup

In **Settings → Install / repair**, BirdNET automatically downloads a private Python 3.11 environment when needed. You do not need to install Python 3.11 separately or change the Python used by NFC Tools. Nighthawk similarly manages its own Python 3.10 environment. Existing working analyzer installations are reused.

Automatic BirdNET setup supports Apple Silicon Macs, 64-bit Intel/AMD Windows, and 64-bit Intel/AMD or ARM Linux, subject to the operating system and processor requirements of TensorFlow. The pinned Analyzer package still requires TensorFlow 2.20 or newer, whose pip packages do not support Intel Macs or native Windows ARM. Installing a newer Python alone does not resolve those limitations. NFC Tools checks known unsupported platforms before downloading BirdNET's environment and verifies that BirdNET starts after installation.

## Your first recording

Make a short test recording first.

1. In **Settings**, set your recording location and microphone, choose where to save files, and install Nighthawk or BirdNET using **Install / repair**.
2. Check the microphone meter on the main page to confirm that your microphone is picking up sound.
3. Run **Readiness Check**.
4. Consider making a short test recording before trying a full night. Start a recording on the main page, let it run for a minute or so, then stop it. Keep NFC Tools running while analysis starts and finishes, then listen to your recording to check the sound. You may not capture any flight calls during this test. If no calls are detected, no call clips will be created; analysis results and status files may still be present.

Readiness also screens the saved sample for persistent broad buzz and regularly
spaced spectral lines, including high-frequency interference. A match produces
a “Possible steady buzz detected (experimental)” note; it does not block recording.
Listen to the sample even when the check passes: the screen can miss unwanted
noise and cannot diagnose grounding. A peak of 0 dBFS alone does not trigger a warning.

Settings changes save automatically, with status beside each section. Text fields save after a short pause; choices and checkboxes save
when changed. Wait for **Saved** before leaving or starting recording/analysis.
If saving fails, your edits stay on the page: correct the indicated field or use
**Retry unsaved changes**. Unfinished settings in another section do not block a
microphone change. Confirm **Input for the next recording** after changing the
microphone; an active recording keeps its existing input and format.

Select the built-in microphone in **Settings → Microphone** to test the app, including the microphone meter and buzz screening in Readiness Check, before attaching an external microphone. An external microphone is recommended for overnight bird recording. In Settings, you can explicitly select microphones labeled “not suitable”; the label is advisory. Automatic selection still excludes these inputs and never falls back to the built-in microphone.

## Recording and reviewing

Schedule recordings using local twilight or fixed times. NFC Tools splits recordings at your selected location's midnight and twilight boundaries to help checklists follow the [eBird Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC).

**Note:** Review clips include up to four seconds of ambient sound before and after each detection. A one-second detection produces up to nine seconds of audio; a three-second detection produces up to eleven seconds.

**Recording options** features two choices:

- **Record now even outside the scheduled window** starts a session immediately.
- **Extend into morning flight** extends recording until two hours after local sunrise, without shortening a later scheduled stop.

The morning flight option is useful for migrants that prefer more daylight, such as winter finches. The NFC counting window remains astronomical dusk to astronomical dawn.

Auto-schedule installs a fixed daily launch time using the start time calculated
when you enable it. That launch time does not move automatically as twilight
changes. Re-enable Auto-schedule to refresh it after changing schedule settings
or as seasonal twilight times shift. The computer must be awake at launch time.
Automatic nightly launch has not yet been tested in real-world use.

### Automated analysis

Analysis normally runs after recording stops. Keep NFC Tools running while it works.

By default, when the computer reports that it is on battery at 10% or below,
NFC Tools stops recording cleanly and defers analysis. Change this behavior in
**Settings → Power & battery**, where you can also defer analysis while on
battery or below a chosen battery level.

To continue analysis with the laptop closed, enable **Settings → Power & battery →
Continue analysis with the laptop lid closed**, then wait for **Saved** before starting analysis
or a new import. This also enables sleep prevention for analysis; battery deferral
and critical-battery policies still apply.

**macOS:** Before leaving the computer unattended, click **Authorize closed-lid
analysis** in Settings and approve the Mac password dialog. Authorization lasts
until NFC Tools quits. You must also enable **Continue analysis with the laptop lid
closed** and wait for **Saved**. If authorization fails or is declined, analysis
can continue with the lid open.

This approval applies only to the running app process. Automatically launched
sessions run in a separate process and cannot reuse it; keep the lid open for
those sessions.

**Linux:** NFC Tools requests that the system ignore lid closure during analysis,
but desktop power settings may override this.

**Windows:** Also select **Do nothing** for the lid-close action in Power Options.

Keep the laptop on a ventilated surface while analysis runs.

See [closed-lid analysis technical details](docs/closed-lid-analysis.md) for how
sleep prevention works and how to restore normal sleep after an interrupted cleanup.

### BirdNET sensitivity options

BirdNET normally filters likely species using the recording date and recorder
location. Enable **Include all species expected at any time of year at this
location** to remove the seasonal restriction while retaining location filtering.
This option defaults to off and is independent of finch and owl sensitivity.

In **Settings → Analyzers → BirdNET detection thresholds**, independently enable
**Winter finch sensitivity** and **Owl sensitivity** to retain review candidates
at confidence 0.25. Both default to off. Enabled groups are included even when
unexpected for the recording location or season; other species retain the general
threshold and normal location/date eligibility. A general threshold below 0.25
still applies to all species. The included species are listed in Settings; the owl
set covers US/Canada species, including southwestern owls, and the finch set includes
BirdNET's separate redpoll labels.

These options increase false positives and review volume; they do not confirm an
identification. Imported batches preserve the settings selected when the batch is
prepared. Reanalyze existing recordings to recover previously excluded calls.

### Analyze existing audio

You can use **Import Recordings** to analyze existing recordings or resume interrupted analysis. You can also correct or manually specify recording start times, which is useful if your recorder uses UTC or has an inaccurate clock.

Exported clips include recording and identification details. See [clip metadata](README_DEV.md#clip-metadata) for technical details and compatibility notes.

**Always review identifications yourself before reporting observations.** Nighthawk and BirdNET results are suggestions based on machine learning models, not certain species identifications.

## Where results go

Each night gets a dated folder in your chosen save location. Its default is your Desktop.

| Folder or file | Contents |
| --- | --- |
| `audio/` | Recorded WAV files |
| `results/` | Original analyzer results |
| `audio/clips/` | Audio clips grouped by recording start time |
| `logs/` | Recording, analysis, and available weather logs |
| `results/eBird checklists/` | eBird upload files and review CSVs when exports are enabled |
| `review/` | Review CSVs when eBird exports are disabled |
| `NIGHT_STATUS.txt` | A saved snapshot of recording and processing status |

WAV filenames use `<index>_<period>_<YYYY-MM-DD>_<HH-MM-SS>_UTC<±HHMM>.wav`, for example `014_MORNING_FLIGHT_2026-10-25_07-00-00_UTC-0400.wav`. Only recordings inside the NFC counting window contain `NFC`.

Hourly clip folders retain local time and append the corresponding UTC time, for example `01-00-00_UTC-05-00-00` and `01-00-00_UTC-06-00-00` for the two 1 a.m. hours when daylight saving time ends in New York. The parent night date remains local. Older recordings without a UTC offset remain readable and retain their original clip folder naming.

| Period | Local time covered |
| --- | --- |
| `NFC` | Astronomical dusk to astronomical dawn |
| `CIVIL_MORNING` | Astronomical dawn to civil dawn |
| `MORNING_FLIGHT` | Civil dawn to sunrise plus two hours |
| `DAYTIME` | Sunrise plus two hours to civil dusk |
| `CIVIL_EVENING` | Civil dusk to astronomical dusk |

A recording with no review clips may still be awaiting analysis. Check its status before treating an empty folder as having no detections.

## eBird exports

Creating eBird checklist files is optional. Configure your location and country/state codes in Settings, or turn exports off if you only want recordings, analysis, and review clips.

Files named `ebird_record_import_…csv` are for eBird upload; `ebird_review_…csv` files are for your own review. The combined nightly upload can contain multiple checklists for uploading an entire night at once. Species comments include estimated call totals and raw counts by model, while checklist comments note starts and stops at civil twilight, astronomical twilight, or midnight before the available weather conditions.

BirdNET and eBird sometimes use different names for the same bird. NFC Tools translates BirdNET detections into eBird names for export. Uncertain matches are flagged for review and excluded from eBird upload files.

The BirdNET team plans to align species names and labels with AviList as V3.0 rolls out across its tools. I'll refine this mapping and documentation after those updates are available. See the [BirdNET team's update](https://github.com/orgs/birdnet-team/discussions/57#discussioncomment-19537566).

To apply updated name mappings to recordings you've already analyzed, regenerate their exports. See [BirdNET taxonomy mapping](README_DEV.md#birdnet-taxonomy-mapping) for technical details.

Species comments begin with `NFC <count>` during the nighttime counting window—for example, `NFC 10 (estimated) | Nighthawk 10 | BirdNET 4`. Outside that window, comments use `Unique detections 10 (estimated) | Nighthawk 10 | BirdNET 4`. Checklist comments begin with `Awaiting manual review`; this refers to identification review, not a required call-count step.

Counts are automatic estimates of detected events. Each connected group of overlapping or touching windows for the same species and recording counts once, within or across models. Windows separated by a positive gap count separately. A chain of overlapping windows can contain several calls, so this approach can undercount repeated calls. It does not establish individual bird counts or flight-call behavior. The original analyzer results and raw model totals are preserved.

No audio review or count entry is required to generate these estimates or export species. Upload abundance defaults to `X`; estimates belong in species comments. Species with uncertain taxonomy mappings remain excluded until their identification mapping is resolved.

`<night folder>/review/call_count_review.csv` remains available for optional corrections. Each row includes an automatic estimate and the source detection windows. To override a group, enter a nonnegative integer in `reviewed_call_count`; `0` rejects the group. Leave the column blank to use the automatic estimate. Save without changing group IDs, then regenerate exports using:

```bash
nfc prepare-ebird "/path/to/night" --state-province MA
```

Use your own night folder and state/province code. The command defaults to country
code `US`; for another country, add `--country-code` with its two-letter code,
for example `--country-code CA` for Canada.

Overrides apply to the entire group, not each model. A species whose groups total zero is omitted. Comments retain the `(estimated)` qualifier, including when an override is present. General review CSVs retain raw per-model `count` values, while mapped species comments show the combined species estimate.

Saved overrides are reused only for unchanged detection groups. If source results change, affected groups return to automatic estimates, and previous reviewed CSV contents are backed up alongside the file. The count CSV is also produced with eBird exports disabled. I have tested grouping and export behavior with automated fixtures, not established count accuracy on representative nights.

NFC Tools currently uses the eBird NFC protocol even for recordings outside the counting window. This is a provisional choice: eBird's guidance limits NFC counts to astronomical dusk through astronomical dawn and calls for separate twilight checklists. Checklists outside that window include the applicable comment:

- “Evening twilight recording outside strict NFC counting window.”
- “Morning twilight recording outside strict NFC counting window.”
- “Morning recording outside strict NFC counting window.”
- “Daytime recording outside strict NFC counting window.”

**Regional rarity comments** flag species that your region's eBird filter marks as rare on the recording date. These species receive a reminder in their exported comments: “Flagged rare for species and/or date. Provide recording or description of the call.”

To use this feature, ask your regional eBird reviewer whether they're willing to share the region's rarity filter as a CSV file. Import it in **Settings**, specify its region, confirm that it covers your recording and eBird location, and enable reminders.

The filter is optional. It flags species or dates requiring documentation, but does not flag unusually high counts. Results depend on the filter you import and may differ from eBird's current filters. See [regional rarity filters](README_DEV.md#regional-rarity-filters) for supported file formats and matching details.

## Experimental wingbeat detection

The built-in wingbeat detector looks for repeated sound pulses and supporting frequency patterns, marking possible wingbeats as `WING` for listening review. These candidates appear in review files, not eBird upload files, and are not species identifications. **False positives are still very common**, and some actual wingbeats may be missed.

See the [wingbeat detector README](README_WINGBEATS.md) for detection criteria, limitations, development details, and recording-source credits.

## Help and development

Use **Diagnostics** for troubleshooting and [GitHub Issues](https://github.com/AndrewW-NFC/NFC-tools/issues) for questions or bug reports.

- [Developer guide and command-line tools](README_DEV.md)
- [Changelog](CHANGELOG.md)
- [Species codes and eBird import reference](docs/reference/nighthawk-species-family-lookup.md)
- [Macaulay Library Audacity tutorial](https://www.macaulaylibrary.org/resources/audio-editing-tutorials/editing-in-audacity/)
- [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/)

I also help administer an NFC Discord community. Ask through a GitHub Issue if you would like an invitation.

## License

NFC Tools is source available under the [PolyForm Noncommercial License 1.0.0](LICENSE).
The license permits noncommercial use and expressly permits use by the listed
research, educational, charitable, environmental protection, and government
organizations regardless of funding. The license text governs these permissions.

For commercial use outside those permissions, contact me at
[akwhitacre@gmail.com](mailto:akwhitacre@gmail.com) for a separate license.
See [NOTICE](NOTICE) for attribution and scope. Third-party analyzers, models,
and assets have separate terms; my commercial license does not override them.
Earlier MIT releases and the historical `nfc-tools-previous/` snapshot retain
their original permissions.
