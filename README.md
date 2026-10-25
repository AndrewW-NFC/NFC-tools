# NFC Tools

[![CI](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml)

NFC Tools records and analyzes nocturnal flight calls on your computer. It uses [Nighthawk](https://github.com/bmvandoren/Nighthawk) and [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer), creates audio clips for review, and prepares optional eBird bulk-upload files. It also includes an experimental wingbeat detector.

The app opens in your browser. Recording and analysis run on your computer. Recording and analysis can run offline after NFC Tools and the analyzers are installed. Internet access is needed for initial setup and optional features such as maps and weather data.

NFC Tools has been used smoothly for thousands of recordings on macOS. Linux has been tested in an Ubuntu virtual machine, but not yet for real overnight recording. Windows passes automated tests but still needs real-world testing. I would welcome feedback from Windows users on whether NFC Tools runs as expected on their machines.

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

Open your command-line tool and enter/paste this:

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

Open PowerShell and enter this:

```powershell
cd $HOME\Desktop\nfc-tools
.\.venv\Scripts\Activate.ps1
nfc-tools
```

These commands assume you installed NFC Tools in the `nfc-tools` folder on your Desktop. If you chose another location, adjust the `cd` command.

The app opens at [http://127.0.0.1:8765/](http://127.0.0.1:8765/).

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

### Analyze existing audio

You can use **Import Recordings** to analyze existing recordings or resume interrupted analysis. You can also correct or manually specify recording start times, which is useful if your recorder uses UTC or has an inaccurate clock.

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

WAV filenames use `<index>_<period>_<YYYY-MM-DD>_<HH-MM-SS>.wav`, for example `014_MORNING_FLIGHT_2026-10-25_07-00-00.wav`. Only recordings inside the NFC counting window contain `NFC`.

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
