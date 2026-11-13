# Experimental wingbeat detector

The built-in detector marks possible wing sounds as `WING` for listening review.
It does not identify species or confirm that a bird was flying. Candidates appear
in review files and clips, not eBird upload files, and do not contribute to NFC
or flight-call totals.

**False positives are still very common.** Rain, insects, bat calls, machinery,
footsteps, and other repeating sounds can trigger detections. Real wing sounds
can also be missed. Listen to each candidate before drawing conclusions.

## Using the detector

Select **Possible wingbeats** under **Settings → Analyzers**, or choose it when
importing recordings. It is included in new settings for the normal app and
preselected for new imports; saved selections still apply. The isolated
development profile defaults to BirdNET only.

No separate model download is required. The detector uses NFC Tools' existing
FFmpeg and NumPy dependencies. It scans the full recording, so enabling it adds
processing time even when it finds no candidates.

Results are saved under `results/wingbeats/<recording>/` as a CSV and Audacity
labels. Review clips appear under `audio/clips/<segment-folder>/`, with up to
four seconds of context before and after the detected interval. WING candidates
also appear in review CSVs. See [where results go](README.md#where-results-go).

The `periodicity` score describes repetition in the sound. It is not the
probability that a detection is a wingbeat, and detection totals are not counts
of birds or individual wing strokes.

## How detection works

This is a rule-based screen, not a trained machine learning classifier. It checks
overlapping 1-, 1.5-, and 2-second windows for several distinct pulses, changes in
loudness, a repeating rhythm, and supporting frequency content. At least one
second of audio is needed. One qualifying window can trigger a detection;
overlapping detections are merged.

There are two main ways a sound can qualify:

- **Broadband pulses:** energy across roughly 150–3,000 Hz that pulses together
  in several frequency bands.
- **Pulses near a spectral peak:** repeated energy in the 700–9,500 Hz search
  range, with nearby noise that rises and falls with it.

Additional checks examine signal strength, frequency spread, and interference.
Some less regular rhythms can pass when other evidence is stronger. A separate
upper-frequency route uses stricter pulse and bandwidth checks. Neither a bird
call nor a wing whistle is required.

The detector also checks for changing narrow sounds that can resemble broader
pulses when averaged over time. This rejects some call-like false positives,
but does not identify or reliably exclude every bird call, insect, or footstep.
Quiet, brief, irregular, or out-of-range wing sounds may be missed.

Exact thresholds and implementation details are linked from the
[developer guide](README_DEV.md#experimental-wingbeat-screening). They are
engineering choices, not established biological boundaries.

## Development and evaluation

Development uses wingbeat recordings from xeno-canto and the Macaulay Library,
along with FSD50K environmental recordings used to examine false positives.
The target includes mechanical wing sounds such as wing–water contact, not only
sounds from birds in flight.

Evaluation reports describe results on selected recordings, some of which were
also used to tune the rules. They do not establish accuracy or review workload
for an unattended night at a new site. Automated tests check software behavior;
field evaluation requires listening to both flagged and unflagged audio.

## Source recordings for development and evaluation

**Macaulay Library.** Wingbeat recordings: Cornell Lab of Ornithology | Macaulay Library. Individual recordings are cited by species, recordist, and linked catalog number—for example: Mallard by Sławomir Karpicki; Cornell Lab of Ornithology | Macaulay Library ([ML645008811](https://macaulaylibrary.org/asset/645008811)). The [accompanying recording list](docs/wingbeat-recording-sources.md) provides citations for all 20 pilot recordings.

**xeno-canto.** Wingbeat recordings: [xeno-canto](https://xeno-canto.org/). Individual recordings are identified by recordist and linked XC catalog number, with the applicable license recorded in the source catalog.

**FSD50K.** Environmental-sound recordings: Fonseca, E., Favory, X., Pons, J., Font, F., & Serra, X. (2020). *FSD50K* (Version 1.0) [Data set]. Zenodo. [doi:10.5281/zenodo.4060432](https://doi.org/10.5281/zenodo.4060432).

**FSD50K reference publication.** Fonseca, E., Favory, X., Pons, J., Font, F., & Serra, X. (2022). FSD50K: An open dataset of human-labeled sound events. *IEEE/ACM Transactions on Audio, Speech, and Language Processing, 30*, 829–852.

## Further reading

- [NFC Tools installation and usage](README.md)
- [Developer guide: wingbeat implementation and evaluation links](README_DEV.md#experimental-wingbeat-screening)
- [Historical wingbeat research audit](docs/wingbeat-research-audit.md)
- [October 16 waterfowl evaluation](docs/evaluations/wingbeat-waterfowl-2026-10-16/release-report.md)
- [Optional wingbeat research data and restore instructions](research/archive/2026-09-wingbeat-handoff/README.md)
