# Guarded call exclusion — November 6, 2026

Implemented a conservative rejection check for moving, spectrally concentrated
sounds with negligible low-frequency energy. The supplied development clips
flagged by WING fall from **33 to 19**, and the nine additional robin clips from
**9 to 3**. All detection intervals in **243 T7 regression recordings** and
**48 gain/timing variants of four genuine-wingbeat controls** remain unchanged.
Both likely-footstep clips still trigger. This is a partial false-positive
reduction, not a robin classifier or a guarantee about future recordings.

## Fresh streaming results

| Supplied group | Clips | Flagged before | Flagged after |
|---|---:|---:|---:|
| Descriptive diagnosis, excluding “faint” | 7 | 7 | 3 |
| Varied WING development clips | 34 | 26 | 16 |
| Additional robin examples | 9 | 9 | 3 |
| Likely footsteps on leaves | 2 | 2 | 2 |

The six excluded “faint” clips were not used. The eight varied clips that did not
trigger before are not counted as successful suppressions. Audio and original
labels were not modified. Mixed-species labels and tentative footstep identity
remain uncertain; the detector does not identify the animal or sound source.

The T7 comparison includes 99 xeno-canto recordings, 100 environmental recordings,
11 species reference recordings, 11 discrete-sound negatives, 18 waterfowl pilot
recordings, three field crops and one insect control. There are **zero interval
changes**, with 176/243 recordings flagged both before and after. This corpus
includes negatives and already-missed positives: it is not 243 successful
wingbeat detections. The new rule does not improve those existing environmental
false positives. Prior label caveats for the pilot, including not treating
Mute Swan/Wood Duck/Cinnamon Teal as negative training, still apply.

## Rule and implementation

For a band that otherwise passes accompaniment screening, inspect 512-sample
Hann-windowed spectra at 24 kHz with 120-sample hops (about 21 ms frames and
5 ms hops). Use the region within 1,200 Hz of the band's tracked residual center,
bounded by 700–9,500 Hz. Subtract the per-frequency 20th-percentile background,
clip negative excess to zero, and select the loudest quarter of excess-energy
frames. Measure:

1. The 10th–90th percentile range of the spectral centroid across those frames.
2. Median per-frame effective bandwidth divided by the effective bandwidth of
   their averaged spectrum. Effective bandwidth uses squared total power divided
   by the sum of squared bin powers; its bin spacing cancels in the ratio.

Reject that band only when **all three** conditions hold:

- 150–600 Hz energy relative to 150–3,000 Hz is **below 0.0005 (0.05%)**;
- centroid range is **at least 700 Hz**;
- instantaneous/averaged bandwidth ratio is **at most 0.80**.

The measurement describes frequency variation across loud frames in a window;
it is not a segmentation or recognition of individual robin calls. Broadband
acceptance remains independent. Other accepted bands still count. Motion is
computed only for potentially passing, very-low-bass bands, with one short-frame
FFT shared across eligible bands in a window. Neutral motion defaults on other
features mean “not needed for this veto,” not a measured absence of movement.

Stable whistles and stable localized noise without bass are preserved. The bass
guard prevents applying this rule to most field wingbeats whose frequency
content also changes. These are empirical engineering thresholds. Unrelated
bass can also prevent rejection of a call; that conservative limitation is
preferable to claiming that all high-frequency moving sounds are vocalizations.

## Development decisions and limits

A frequency-motion check alone rejected genuine field passages, including a
Mallard passage. A bass guard limited that damage; the final guard is more
conservative than the detector's ordinary 0.5% low-band support threshold.
A 600 Hz excursion cutoff also rejected one existing synthetic positive with
synchronized separate lobes. The final 700 Hz cutoff preserves that case and
accepts reduced robin suppression. The earlier blanket bass requirement remains
rejected because it destroyed stable, no-bass localized-pulse sensitivity.

Thresholds were selected using these development examples and retention
controls. The additional robin set was previously inspected and is not an
untouched holdout. Some excerpts share exact audio, as recorded in the preceding
diagnosis. Neither clip counts nor variants estimate independent field accuracy.
Performance on new sessions, microphones and filtering conditions remains
unestablished, and this is not a new full-night evaluation.

## Gain and alignment checks

Gains 0.1, 1 and 3 were crossed with leading silence of 0, 0.125, 0.5 and
0.75 seconds, without clipping float PCM. These are correlated variants.

| Set | Variants | Flagged before | Flagged after |
|---|---:|---:|---:|
| Seven diagnosis clips | 84 | 81 | 39 |
| Nine additional robin clips | 108 | 102 | 33 |
| Three genuine field crops | 36 | 33 | 33 |
| Local Mute Swan wingbeats | 12 | 9 | 9 |

All 48 genuine-wingbeat variants preserve their full baseline intervals, not
just file-level detection. Baseline misses remain misses. Some robin clips that
are fully suppressed at the original alignment still trigger at other
alignments; those residual detections are included above. The two likely-footstep
clips retain their original detection intervals.

## Verification

- **1,038 fresh streaming runs:** before/after on 243 T7 recordings plus 276
  supplied/control variants. Before uses the current implementation with only
  the new veto disabled in isolated evaluation worker processes; after enables
  the veto. This preserves all other contemporary acceptance behavior.
- All T7 decoded PCM hashes match the prior source provenance. Every candidate
  interval is contained within a baseline interval; this rejection-only change
  introduces no new intervals in the evaluated set.
- Old October feature caches differ from today's baseline in 39 recordings;
  they lack the subsequently added 2.2–3.5 kHz search band. They were used only
  for exploration. The reported results are fresh before/after streams.
- Full Python suite: **1,108 passed, 3 skipped**. A subsequent targeted run of
  **26 motion tests passed**, including the newly added research-export test.
  This is an overlapping test count, not 1,134 distinct tests.
- Checks cover gain invariance, cache consistency, a synthetic swept sound that
  previously passed, retained broadband wings overlapping that sound, silent
  inputs, measured robin/field features, existing no-bass controls and research
  diagnostics. Python F checks and diff-whitespace checks passed.

`results.json` contains compact intervals, source fingerprints, all supplied
variants, thresholds and production-source hashes. Detailed measurements and
logs are stored on T7:

`/Volumes/T7/Wingbeats detector/analysis-results/2026-11-06-robin-exclusion/`

Source audio is not copied into the repository. Application processes and
recording schedules were not restarted or changed; this change is in the local
source checkout, not a claim that an already-running packaged app has reloaded it.

## Reproduction

The supplied audio now resides, extracted, at
`/Volumes/T7/Wingbeats detector/audio-library/robin-training/`, with the additional
set under `Test against/`. The verifier resolves those files and checks each
against the original SHA-256. Original ZIP names in historical provenance remain
unchanged; ZIP-based input is also supported.

From the repository root, with T7 connected, use new output directories:

```sh
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-06/exclusion/verify_field.py --output /tmp/robin-field-check
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-06/exclusion/verify_supplied.py --audio-directory '/Volumes/T7/Wingbeats detector/audio-library/robin-training' --field-results /tmp/robin-field-check --output /tmp/robin-supplied-check
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-06/exclusion/summarize.py --field-results /tmp/robin-field-check --supplied-results /tmp/robin-supplied-check --output /tmp/robin-exclusion-summary.json
```

The baseline diagnostic reports in the parent directory intentionally retain
the pre-change measurements. Rerunning their scripts on the modified detector
will produce new results and must not overwrite historical evidence.
