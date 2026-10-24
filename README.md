# NFC Tools

[![CI](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/AndrewW-NFC/NFC-tools/actions/workflows/ci.yml)

NFC Tools records and analyzes nocturnal flight calls on your computer. It uses [Nighthawk](https://github.com/bmvandoren/Nighthawk) and [BirdNET-Analyzer](https://github.com/birdnet-team/BirdNET-Analyzer), creates audio clips for review, and prepares optional eBird bulk-upload files. It also includes an experimental wingbeat detector.

The app opens in your browser, but recording and analysis run locally. Your audio stays on your computer unless you choose to share it elsewhere.

## Getting started

You need Python 3.10 or newer, a microphone, enough space for overnight WAV recordings, and a computer that can stay awake overnight. Internet access is needed for setup, analyzer installation, maps, and weather data. Recording and analysis can work offline after setup.

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

On the main page, **Recording options** groups two independent choices:

- **Record now even outside the scheduled window** starts this session immediately.
- **Include morning flight recordings** continues until **two hours after local sunrise**, without shortening a later scheduled stop. It defaults to off and is remembered for automatically scheduled sessions too. The preview shows when NFC counting ends and when recording stops. Change this option while the recorder is idle.

The NFC counting window remains astronomical dusk to astronomical dawn. The morning extension is intended to sample early morning movement, including winter finches; it does not extend the NFC counting window.

Analysis normally runs after recording stops. Keep the app running while it works; power settings can defer analysis when the computer is on battery. Follow recording and analysis status on the main page.

To process existing audio, including correcting recorder-clock errors, use **Import Recordings**. Imports preserve your original files and can resume interrupted processing. A gentle “Slow ding” by KoiRoylers plays once when the entire import batch finishes successfully, even if the browser page is closed. Set `notifications.on_batch_complete: false` in your configuration to mute it. Sound attribution and license are in [the sound credits](src/nfc_tools/data/sounds/README.md).

**Always review identifications before reporting observations.** Analyzer results are suggestions based on machine learning models, and NFC Tools does not upload checklists to eBird for you.

## Where results go

Each night gets a dated folder in your chosen save location, which defaults to the Desktop.

| Folder or file | Contents |
| --- | --- |
| `audio/` | Recorded WAV files |
| `results/` | Original analyzer results |
| `audio/clips/` | Audio clips grouped by recording start time |
| `logs/` | Recording, analysis, and available weather logs |
| `results/eBird checklists/` | eBird upload files and review CSVs when exports are enabled |
| `review/` | Review CSVs when eBird exports are disabled |
| `NIGHT_STATUS.txt` | A saved snapshot of recording and processing status |

New WAV filenames use `<index>_<period>_<YYYY-MM-DD>_<HH-MM-SS>.wav`, for example `014_MORNING_FLIGHT_2026-10-25_07-00-00.wav`. Only recordings inside the NFC counting window contain `NFC`.

| Period | Local time covered |
| --- | --- |
| `NFC` | Astronomical dusk to astronomical dawn |
| `CIVIL_MORNING` | Astronomical dawn to civil dawn |
| `MORNING_FLIGHT` | Civil dawn to sunrise plus two hours |
| `DAYTIME` | Sunrise plus two hours to civil dusk |
| `CIVIL_EVENING` | Civil dusk to astronomical dusk |

The date and time are the actual recording start. Segment numbers continue within the session's audio folder, including across midnight. Files split at period boundaries; long recordings and imports use solar boundaries for each date, including daytime audio. The morning-flight checkbox controls the scheduled stop, not how existing audio is classified. Older filenames remain readable; existing files are not renamed. New filenames use period labels instead of the former configurable prefix.

A recording with no review clips may still be awaiting analysis. Check its status before treating an empty folder as having no detections.

## eBird exports

Creating eBird checklist files is optional. Configure your location and country/state codes in Settings, or turn exports off if you only want recordings, analysis, and review clips.

Files named `ebird_record_import_…csv` are for eBird upload; `ebird_review_…csv` files are for your own review. The combined nightly upload can contain multiple checklists for uploading an entire night at once. Species comments include call counts, while checklist comments note starts and stops at civil twilight, astronomical twilight, or midnight before the available weather conditions.

Flight-call species comments use `NFC 12` inside the counting window and `Flight call 12` outside it; BirdNET detections retain their separate label. Periods remain on separate checklists, marked incomplete. **The NFC protocol is provisionally retained for recordings outside the strict window pending guidance from eBird; this is not confirmation that eBird accepts daytime remote recordings under that protocol.** These checklists include the applicable comment:

- “Evening twilight flight calls outside strict NFC counting window.”
- “Morning twilight flight calls outside strict NFC counting window.”
- “Morning flight calls outside strict NFC counting window.”
- “Daytime flight calls outside strict NFC counting window.”

No unattended-recording statement or duplicate start, end, or duration text is added; checklist fields retain timing and duration information.

After uploading, if needed, use eBird’s **Fix Locations** step to confirm the correct personal location or public hotspot. Review identifications and add supporting recordings or descriptions in eBird.

**Regional rarity comments are undergoing testing and are not ready for broader distribution.** This uses eBird regional reviewer-provided data to add rarity reminders to species comments. It has been tested only for Middlesex County, Massachusetts, so far. Support for different eBird regional reviewers’ export formats has not yet been established.

## Experimental wingbeat detection

The built-in wingbeat detector marks possible wingbeats as `WING` for listening review. These candidates appear in review files, not eBird upload files, and are not species identifications.

**Most suggested wingbeat detections so far are false positives.** Calls, bats, rain, machinery, and rustling can trigger it; some actual wingbeats may be missed.

The detector has been developed and evaluated using wingbeat recordings sourced from xeno-canto and the Macaulay Library, as well as FSD50K recordings of potential false positives such as insects, rain, tools, and mechanical ticking. The Central European Birds sound archive is available for future evaluation; it has not yet been used to tune the detector.

Shorter listening windows now recover some brief passages: detection increased from 40 to 44 of 76 confirmed passages in a selected review set, with 14 additional seconds of false alarms. This is a modest improvement, not a general accuracy estimate; see the [evaluation](docs/evaluations/wingbeat-annotation-candidate-2026-10-11/report.md).

**Note:** Wingbeat detection adds substantial processing time, even when it finds no candidates. Consider leaving it off in the analyzer settings if you are not expecting duck flyovers.

### What triggers a WING detection?

The detector looks for repeated sound pulses in overlapping 1-, 1.5-, and 2-second listening windows. A sample must contain at least one second of audio, and a window must meet these requirements:

- **Several distinct pulses:** usually at least four, with repetition searched at roughly 2–20 pulses per second.
- **Noticeable loudness changes:** the quieter envelope level must be at least 25% below the louder level.
- **A repeating pattern:** normally a correlation score of at least 0.60 at one pulse period and 0.35 at two periods. Less regular pulses can qualify when other acoustic evidence is stronger.
- **Supporting frequency content:** either broadband flapping-like pulses across 150–3,000 Hz, synchronized in at least three frequency bands, or pulses associated with a spectral feature in the 700–9,500 Hz search range and nearby noise that rises and falls with them. Additional checks assess low-frequency support, noise strength, bandwidth, and spectral shape. One upper-frequency detection route requires at least six pulses.
- **Enough measurable signal:** the internal peak-envelope value must reach 0.0001. This is a processing threshold, not a microphone loudness or decibel requirement.

A single qualifying window triggers a detection; overlapping detections are merged. A bird call, species identification, or wing whistle is not required.

These are provisional screening thresholds, not a calibrated classifier. The reported periodicity score measures pulse repetition, not the probability that a sound is a wingbeat. **WING means “possible wingbeats—manual review required.”** Other repetitive sounds can meet these conditions.

### Recording sources

**Macaulay Library.** Wingbeat recordings: Cornell Lab of Ornithology | Macaulay Library. Individual recordings are cited by species, recordist, and linked catalog number—for example: Mallard by Sławomir Karpicki; Cornell Lab of Ornithology | Macaulay Library ([ML645008811](https://macaulaylibrary.org/asset/645008811)). The [accompanying recording list](docs/wingbeat-recording-sources.md) provides citations for all 20 pilot recordings.

**xeno-canto.** Wingbeat recordings: [xeno-canto](https://xeno-canto.org/). Individual recordings are identified by recordist and linked XC catalog number, with the applicable license recorded in the source catalog.

**FSD50K.** Environmental-sound recordings: Fonseca, E., Favory, X., Pons, J., Font, F., & Serra, X. (2020). *FSD50K* (Version 1.0) [Data set]. Zenodo. [doi:10.5281/zenodo.4060432](https://doi.org/10.5281/zenodo.4060432).

**FSD50K reference publication.** Fonseca, E., Favory, X., Pons, J., Font, F., & Serra, X. (2022). FSD50K: An open dataset of human-labeled sound events. *IEEE/ACM Transactions on Audio, Speech, and Language Processing, 30*, 829–852.

## Platform status

NFC Tools has been used for repeated overnight recordings on macOS. Linux has been tested in an Ubuntu virtual machine, but not yet for real overnight recording. Windows passes automated tests but still needs real-world testing.

Automatic nightly launch has not yet been tested.

## Help and development

Use **Diagnostics** for troubleshooting and [GitHub Issues](https://github.com/AndrewW-NFC/NFC-tools/issues) for questions or bug reports.

- [Developer guide and command-line tools](README_DEV.md)
- [Changelog](CHANGELOG.md)
- [Species codes and eBird import reference](docs/reference/nighthawk-species-family-lookup.md)
- [Wingbeat research methods and limitations](docs/wingbeat-research-audit.md)
- [Optional wingbeat research data and restore instructions](research/archive/2026-09-wingbeat-handoff/README.md)
- [Macaulay Library Audacity tutorial](https://www.macaulaylibrary.org/resources/audio-editing-tutorials/editing-in-audacity/)
- [Nocturnal Flight Calls of North America](https://nocturnalflightcalls.com/)

The maintainer also helps administer an NFC Discord community. Ask through a GitHub Issue if you would like an invitation.
