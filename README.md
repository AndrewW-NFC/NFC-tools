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
2. Run **Readiness Check**, then check the microphone meter on the main page.
3. Make a short recording, stop it, and let analysis finish. Review the resulting clips and CSVs before trying a full night.

A built-in microphone is enough to test the app. An external microphone is recommended for overnight bird recording.

## Recording and reviewing

Schedule recordings using local twilight or fixed times. NFC Tools splits recordings at your selected location's midnight and twilight boundaries to help checklists follow the [eBird Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC).

**Note:** NFC Tools extends the default clip duration for Nighthawk and BirdNET to 9 seconds. This is to comply with the Cornell Lab's request that clips have ambient sound before and after the detection.

**Recording options** features two choices:

- **Record now even outside the scheduled window** starts a session immediately.
- **Include morning flight recordings** extends recording until two hours after local sunrise, without shortening a later scheduled stop.

The morning flight option is useful for migrants that prefer more daylight, such as winter finches. The NFC counting window remains astronomical dusk to astronomical dawn.

Automatic nightly launch has not yet been tested in real-world use.

### Automated analysis

Analysis normally runs after recording stops. Keep NFC Tools running while it works.

To continue analysis with the laptop closed, enable **Settings → Power & battery →
Continue analysis with the laptop lid closed**, then save before starting analysis
or a new import. This also enables sleep prevention for analysis; battery deferral
and critical-battery policies still apply.

On macOS, approve the administrator prompt when analysis starts before closing the
lid. NFC Tools temporarily disables system sleep with `pmset` and an independent
watchdog restores the previous setting after analysis, cancellation, or app exit.
Concurrent analyses share the override until the last one finishes. Keep the laptop
on a ventilated surface. If permission is declined, analysis continues but the lid
must stay open; the session log explains the failure. Linux uses a systemd lid
inhibitor (desktop policies may override it). On Windows, also select **Do nothing**
for the lid-close action in Power Options.

If macOS loses power or the privileged watchdog is forcibly killed, automatic
restoration cannot run. To re-enable normal sleep in that case, run
`sudo pmset disablesleep 0` and remove the stale guard with
`sudo rmdir /var/run/nfc-tools-closed-lid.lock`.

### Analyze existing audio

You can use **Import Recordings** to analyze existing recordings or resume interrupted analysis. You can also correct or manually specify recording start times, which is useful if your recorder uses UTC or has an inaccurate clock.

Exported WAV clips carry embedded metadata without changing their filenames: call time,
source recording and detection/clip offsets, configured site, analyzer suggestion and
score when available, and NFC Tools version and repository
link. A readable summary is stored in WAV `LIST-INFO` comments; the `nfct` chunk
contains UTF-8 JSON using schema `nfc-tools.clip`, version 1. Compatible metadata
inspectors can display the comment; ordinary players may ignore these fields.

Call timestamps come from the source filename, including its UTC offset when present.
Legacy filenames without an offset are explicitly marked as having an unknown timezone.
Site values describe the configuration used at export. Unavailable detector model versions
are stored as null. Weather and acoustic conditions are not included in this first version.
Metadata is added to newly exported clips; existing clips are unchanged until re-exported.

**Clip metadata must never contain review information**, in this or future schema
versions: no review status, reviewer identity, accepted/rejected decisions, confirmed
identification, or review notes. Detection suggestions remain analyzer output.

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

Files named `ebird_record_import_…csv` are for eBird upload; `ebird_review_…csv` files are for your own review. The combined nightly upload can contain multiple checklists for uploading an entire night at once. Species comments include call counts, while checklist comments note starts and stops at civil twilight, astronomical twilight, or midnight before the available weather conditions.

Species comments for flight calls identified by Nighthawk use `NFC 12` inside the counting window and `Flight call 12` outside it. BirdNET detections use a different label, since BirdNET is not trained specifically on NFCs. **NFC Tools provisionally retains the eBird NFC protocol for recordings outside the strict counting window.** This is an application behavior, not confirmation that eBird endorses that protocol for daytime recordings; the linked eBird guidance limits NFC counts to astronomical dusk through astronomical dawn and calls for separate twilight checklists. Such checklists include the applicable comment:

- “Evening twilight flight calls outside strict NFC counting window.”
- “Morning twilight flight calls outside strict NFC counting window.”
- “Morning flight calls outside strict NFC counting window.”
- “Daytime flight calls outside strict NFC counting window.”

**Regional rarity comments are undergoing testing.** If you know your eBird reviewer, you might politely ask if they're willing to share your region's rarity filter. It has been tested only for Middlesex County, Massachusetts, so far. (Thank you, Jason.)

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

The maintainer also helps administer an NFC Discord community. Ask through a GitHub Issue if you would like an invitation.

### BirdNET sensitivity options

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
