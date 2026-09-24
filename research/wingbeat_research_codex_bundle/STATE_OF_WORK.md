# WING research: state of work as of 2026-09-24

## Objective
Improve the experimental WING detector in NFC Tools using empirical data, but **do not change any WING detection decisions yet**. The current phase is instrumentation and measurement.

## Current production detector
The existing WING implementation is rules-based. It has a broadband rhythmic route plus a tonal/accompaniment route. The research scanner in this bundle treats the repository's existing `screen_window()` / `detect_stream()` behavior as authoritative and records additional measurements after the fact.

## FSD50K work already completed
The FSD50K development set contains 40,966 WAV files. The user's local copy is on the T7 drive at:

`/Volumes/T7/FSD50K/FSD50K.dev_audio`

A first-pass scan with the unmodified WING detector completed over all 40,966 development files. The scan CSV is included in this bundle as:

`data/fsd50k_wing_scan_dev.csv`

Summary of that scan:

- 40,966 files analyzed
- 3,923 files triggered WING
- 4,897 merged WING candidate intervals
- 3,343 triggering files have no FSD50K `Animal` label and are the current environmental hard-negative candidate set

The FSD50K **evaluation** set has intentionally not been used and should remain untouched for later independent evaluation.

## Xeno-canto wingbeat corpus
The corpus contains 958 successfully downloaded audio files known at the *recording level* to contain wingbeats. Many recordings also contain calls, songs, or other sounds; therefore a recording-level wingbeat label is a **weak label** and does not make every 2-second window a positive wingbeat example.

A research instrumentation pass has already been run over the 958 files. Its outputs are included here:

- `data/xc_wingbeat_research_files.csv`
- `data/xc_wingbeat_research_windows.csv.gz`

Summary:

- 958 recordings
- 44,280 two-second analysis windows
- 3,996 windows accepted by current WING
- 1,522 merged WING candidate events
- 467 of the 958 recordings had at least one current-WING candidate

These figures are **not** sensitivity estimates because precise wingbeat timestamps are not yet available for most recordings.

## Research instrumentation
`tools/wingbeat_research_scan.py` is a research scanner, not a production detector replacement. It records:

- the current WING decision, score, and route
- current broadband feature values and failed gates
- beat-rate and inter-pulse-interval measurements
- pulse timing, width, attack/decay, amplitude variation, waveform impulsiveness and biphasic morphology
- spectral centroid, bandwidth, rolloff, entropy, crest, flux, and harmonic-comb diagnostics
- per-band modulation/coherence/synchrony information
- tonal/accompaniment measurements across the existing search bands
- metadata/provenance fields

See `FEATURE_DICTIONARY.md` for the feature schema.

## Immediate next step
Audit/integrate the research scanner in the NFC Tools repository without changing production WING decisions, then run the same instrumentation over the 3,343 FSD50K non-Animal hard negatives on the T7. The output should remain on the T7 because it can be large.

Recommended output directory:

`/Volumes/T7/FSD50K/wing_research_hard_negatives`

## Non-negotiable experimental cautions

1. Do not tune thresholds or train a classifier yet.
2. Do not treat every xeno-canto window as a positive wingbeat example.
3. Do not use FSD50K eval yet.
4. Preserve provenance so a model cannot simply learn xeno-canto/MP3 versus FSD50K/WAV source differences.
5. Keep the production detector's decisions identical while instrumentation is being added and validated.
6. Add automated regression tests that compare the instrumented path with the existing production path.
