# NFC Tools

[![CI](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml)

NFC Tools records and analyzes nocturnal flight calls on your computer. It uses [Nighthawk](https://github.com/bmvandoren/Nighthawk) and [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer), creates audio clips for review, and prepares optional eBird bulk-upload files. It also includes an experimental wingbeat detector.

The app opens in your browser, but recording and analysis run locally. Your audio stays on your computer unless you choose to share it.

## Getting started

You need Python 3.10 or newer, a microphone, enough space for overnight WAV recordings, and a computer that can stay on overnight. Internet access is needed for setup, analyzer installation, maps, and weather data. Recording and analysis can work offline after setup.

### macOS or Linux

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

### Windows PowerShell

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

If you download the GitHub ZIP instead, extract it and open Terminal or PowerShell in that folder. Start with the virtual-environment command above; skip the clone and directory-change commands.

The app opens at [http://127.0.0.1:8765/](http://127.0.0.1:8765/). To launch it again later, open the project folder, activate the virtual environment, and run `nfc-tools`.

## Make a short test recording first

1. In **Settings**, set your recording location and microphone, choose where to save files, and install Nighthawk or BirdNET using **Install / repair**.
2. Run **Readiness Check**, then check the microphone meter on the main page.
3. Make a short recording, stop it, and let analysis finish. Review the resulting clips and CSVs before trying a full night.

A built-in microphone is enough to test the app. An external microphone is better suited to overnight bird recording.

## Recording and reviewing

Schedule recordings using local twilight or fixed times. NFC Tools splits recordings at midnight and twilight boundaries to help prepare separate checklists for the [eBird Nocturnal Flight Call Count protocol](https://support.ebird.org/en/support/solutions/articles/48000950859-guide-to-ebird-protocols#anchorNFC).

Analysis normally runs after recording stops. Keep the app running while it works; power settings can defer analysis when the computer is on battery. Follow recording and analysis status on the main page.

Use **Import Recordings** to process existing audio, including correcting recorder-clock errors. Imports preserve your original files and support resuming interrupted processing.

**Always review identifications before reporting observations.** Analyzer results are suggestions, and NFC Tools does not upload checklists to eBird for you.

## Where results go

Each night gets a dated folder in your chosen save location, which defaults to the Desktop.

| Folder or file | Contents |
| --- | --- |
| `audio/` | Recorded WAV files |
| `results/` | Original analyzer results |
| `clips/` | Audio clips grouped by recording start time |
| `logs/` | Recording, analysis, and available weather logs |
| `eBird checklists/` | eBird upload files and review CSVs when exports are enabled |
| `review/` | Review CSVs when eBird exports are disabled |
| `NIGHT_STATUS.txt` | A saved snapshot of recording and processing status |

A recording with no review clips may still be awaiting analysis. Check its status before treating an empty folder as no detections.

## eBird exports

Creating eBird checklist files is optional. Configure your location and country/state codes in Settings, or turn exports off if you only want recordings, analysis, and review clips.

Files named `ebird_record_import_…csv` are for eBird upload; `ebird_review_…csv` files are for your own review. The combined nightly upload can contain multiple checklists. Species comments include call counts, while checklist comments include available weather conditions.

After uploading, use eBird’s **Fix Locations** step to confirm the correct personal location or public hotspot. Review identifications and add supporting recordings or descriptions in eBird.

**Regional rarity comments are undergoing testing and are not ready for broader distribution.** This work uses locally supplied reviewer data to add rarity reminders to species comments in bulk uploads. Support for different reviewers’ export formats has not yet been established.

## Experimental wingbeat detection

The built-in wingbeat detector marks possible wingbeats as `WING` for listening review. These candidates appear in review files, not eBird upload files, and are not species identifications.

**Most suggested wingbeat detections so far are false positives.** Calls, bats, rain, machinery, and rustling can trigger it; some actual wingbeats may be missed.

**Note:** Wingbeat detection adds substantial processing time, even when it finds no candidates. Consider leaving it off in the analyzer settings if you are not expecting duck flyovers.

## Platform status

NFC Tools has been used for repeated overnight recordings on macOS. Linux has been tested in an Ubuntu virtual machine, but not yet for real overnight recording. Windows passes automated tests but still needs real-world testing. Automatic nightly launch also needs further testing.

## Help and development

Use **Diagnostics** for troubleshooting and [GitHub Issues](https://github.com/AndrewW-NFC/NFC-tools/issues) for questions or bug reports.

- [Developer guide and command-line tools](README_DEV.md)
- [Changelog](CHANGELOG.md)
- [Species codes and eBird import reference](docs/reference/nighthawk-species-family-lookup.md)
- [Wingbeat research methods and limitations](docs/wingbeat-research-audit.md)
- [Optional wingbeat research data and restore instructions](research/wingbeat_research_codex_bundle/README.md)
- [Macaulay Library Audacity tutorial](https://www.macaulaylibrary.org/resources/audio-editing-tutorials/editing-in-audacity/)
- [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/)

The maintainer also helps administer an NFC Discord community. Ask through a GitHub Issue if you would like an invitation.
