# Wingbeat flatness validation — October 10, 2026

## Outcome

| Recording set | Current (0.30) | Flatness 0.13 | Flatness 0.10 | Guarded 0.13 |
|---|---:|---:|---:|---:|
| positive | 10/11 | 10/11 | 10/11 | 10/11 |
| discrete-negative | 0/11 | 0/11 | 0/11 | 0/11 |
| site-hour | 0/1 | 1/1 | 1/1 | 1/1 |

Counts mean recordings with at least one candidate, not event recall. The eleven confirmed positives retain the same ten detected recordings; bufflehead remains missed. The discrete-sound negatives are eleven user-labeled clips in the earlier evaluation. All 22 source SHA-256 hashes match the September 27 per-file evaluation.

## Full hour

Source: `/Volumes/T7/NFC recordings/2026-10-09/audio/Wingbeats/015_NFC_CIVIL_MORNING_2026-10-10_05-18-13.wav`. Duration: 3600.0 seconds.

- current: None
- flat_013: 53:12–53:14.75
- flat_010: 53:11–53:14.75
- conditional_013: 53:12–53:14.75

The user-labeled positive occupies 53:08–53:22. Candidate intervals outside this annotation are unclassified, not automatically false positives. This hour informed threshold selection and is not an independent holdout.

## Variants and synthetic checks

- current: 0/12 gain/alignment variants overlap the annotation.
- flat_013: 12/12 gain/alignment variants overlap the annotation.
- flat_010: 12/12 gain/alignment variants overlap the annotation.
- conditional_013: 12/12 gain/alignment variants overlap the annotation.

Variants use the 53:04–53:28 crop, gains 0.1/1/3 crossed with leading silence 0/0.25/0.5/0.75 seconds. These correlated transformations are sensitivity checks, not twelve independent recordings. All 122 existing tests in test_wingbeat_call_rejection.py and test_wingbeat_spectral_support.py pass with MIN_PULSE_EXCESS_FLATNESS temporarily set to 0.13 in the test process. They include synthetic patchy calls, weak swept calls, high-pass noise pulses, and positive controls, not real species-labeled call recordings.

## Exact candidate definitions

- Current: unchanged production broadband OR accompaniment screen.
- Flatness 0.13 / 0.10: change only the accompaniment pulse-linked excess-flatness cutoff; every other gate and window schedule remains unchanged.
- Guarded 0.13: retain every current detection, plus a 0.13 route requiring first-period similarity at least 0.70, second-period similarity at least 0.65, and ridge prominence at least 16. This is an exploratory window-level alternative chosen using the new positive; it does not implement cross-window persistence or tracking and has not been independently validated.

## Method and reproducibility

The app FFmpeg decoded source audio at 24 kHz mono float32. The production analysis_windows iterator provides exactly the production schedule, including EOF tails. Full-hour jobs own disjoint 60-second start ranges with two seconds of lookahead; integer-second chunk offsets preserve the original schedule. Results are merged globally across chunk boundaries. Window features are computed once, and the authoritative accompaniment screen is reused for each cutoff by rescaling only its flatness input. The broadband route uses the existing research helper. The first two windows in each of 82 jobs are additionally checked against screen_window, yielding 164 production-decision agreement assertions. None failed.

The included [run.py](run.py) and [variants.py](variants.py) reproduce the evaluation in this workspace with its source paths, writing temporary decoded caches under /tmp/nfc-wingbeat-validation. The main script creates that directory. Source/PCM hashes, per-file results, accepted windows, and test output are included. No audio is included in these report artifacts. Production source files were not changed.

## Missing validation

The 47 osprey/other-vocalization clips, two bat clips, five rain clips, four insect-ticking clips, and preserved wind/cricket caches from the previous study were not located. A filename search and SHA-256 comparison against 26,234 small September WAVs on T7 found no exact matches to the prior source hashes. The user also could not identify the current archive locations. This does not prove the sounds are absent from all recordings or that re-exported equivalents are unavailable. The eleven available discrete clips cannot substitute for those acoustic classes.

## Recommendation

0.13 is a promising experimental cutoff for this event, but this evaluation cannot establish safety against the real call/rain/insect regressions that motivated the 0.30 cutoff. Keep the production threshold unchanged until those negatives are recovered or a replacement labeled field set is evaluated. A guarded route can be investigated further, including sustained rhythm across windows, but the present results do not establish a benefit in specificity. No species identity, calibrated confidence, or general field accuracy is inferred.

From the repository root, with the original recordings available at the recorded paths:

```bash
.venv/bin/python docs/evaluations/wingbeat-flatness-2026-10-10/run.py
.venv/bin/python docs/evaluations/wingbeat-flatness-2026-10-10/variants.py
```

Results: [summary](summary.json), [per-file intervals](per-file-results.csv),
[gain/alignment variants](variants.json), and [synthetic test output](synthetic-tests.log).
