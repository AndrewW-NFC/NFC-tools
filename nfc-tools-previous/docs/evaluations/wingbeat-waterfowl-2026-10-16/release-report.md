# Guarded waterfowl recovery — October 16, 2026

## Shipped change

Enable a guarded alternative for less regular upper-band mechanical pulses, plus
conditional support for moderately uneven pulse spectra. The marked Mallard,
Common Merganser and Pacific Black Duck passages now overlap detections. This is
a sensitivity/review-workload tradeoff, not a trained model or general accuracy
claim. The earlier unrestricted rhythm relaxation was not adopted.

The irregular-pulse route requires a search band starting at least at 3.5 kHz,
first and second repeat correlations of at least 0.45 and 0.25, pulse-excess
flatness at least 0.70, noise coherence at least 0.65, contrast at least 0.30,
noise ratio at least 0.10, low-band fraction at least 0.005, ridge prominence at
least 5, lower-band coherence at least 0.30 and effective lobe width at least
300 Hz. The existing amplitude, pulse-count, modulation, relative peak strength,
residual-bin and spectral-support gates remain. The upper-interference veto is
retained explicitly. These provisional thresholds were developed on this pilot.

The spectral alternative allows excess flatness from 0.20 to 0.30 only with ridge
prominence at least 16, second-repeat correlation at least 0.50 and coherence at
least 0.50. Other gates remain. Neither alternative removes previous acceptance
routes. Research diagnostics use the same authoritative acceptance helpers.

## Requested samples

| Recording | Human passage | Added detection | Gain/timing checks |
|---|---|---|---|
| Mallard, ML645008811 | 28–30 s | 28.75–30.75 s | 12/12 pass; minimum overlap 1.25 s |
| Common Merganser, ML211014411 | 22–24 s | 22.25–23.25 s | 12/12 pass; minimum overlap 1.00 s |
| Pacific Black Duck, ML475055411 | 5–10 s | 7.25–8.75 s | Original recording verified |

Pass means a positive-duration overlap with the human-marked passage. These are
partial recoveries, not complete coverage or exact boundary matches. Gain/timing
checks use gains 0.1, 1 and 3 crossed with leading silence of 0, 0.25, 0.5 and
0.75 seconds, without clipping. Variants are correlated robustness checks, not
additional independent biological examples.

## Results

| Measure | Before | After |
|---|---:|---:|
| Clear pilot passages overlapped | 4/12 | 7/12 |
| Pilot annotated seconds covered | 6.25/74 | 10.00/74 |
| Previously reviewed XC passages overlapped | 44/76 | 45/76 |
| XC negative-labeled recordings flagged | 3/23 | 3/23 |
| Remaining pilot listener-negatives flagged | 0/3 | 0/3 |
| Environmental recordings flagged | 100/100 | 100/100 |
| Discrete-sound controls flagged | 0/11 | 0/11 |
| Confirmed species reference recordings flagged | 10/11 | 10/11 |
| Insect gain/timing variants flagged | 0/12 | 0/12 |
| Known-positive field gain/timing variants flagged | 36/36 | 36/36 |

All baseline intervals were retained. The unchanged environmental file count
hides **62.73 extra detected seconds** across those 100 recordings. These examples
were selected from prior detections; they do not estimate general false-positive
rates. Their labels are inherited from an earlier review with highlighted
intervals. Added detections outside those intervals represent extra review
workload, not independently verified false positives. The XC negative intervals
are unchanged, not just their file-level counts. The additional XC positive is
XC-041. The reference set gains 0.5 detected seconds without changing its count.

The pilot is a development set used to choose these rules. This run covers full
pilot/reference/control recordings and three field crops, not a new full-night
scan. It does not prove how the added review workload transfers to tonight.
Mechanical wing sounds including wing–water contact remain in scope; no new
listener categories were added. Mute Swan, Wood Duck and Cinnamon Teal must not
be used as negative training examples. None-heard judgments retain uncertainty
about faint wing sounds.

## Verification and evidence

- **309 fresh streaming runs**: 18 pilot recordings, 225 baseline regression
  recordings and 66 additional gain/timing variants. Sources were decoded using
  the production 24 kHz mono FFmpeg path; decoded hashes match frozen baselines.
  Every base output agrees exactly with recomputation from frozen features.
- **978 Python tests passed, 3 platform skips** in the local full suite; this
  includes 34 new regression/counterexample tests and the pre-existing untracked
  Macaulay collector tests, which are not included in this commit.
- **38 JavaScript tests passed**. Main/review JavaScript syntax, Python F checks,
  version/dependency consistency and diff-whitespace checks passed.
- Wheel build and isolated installed-wheel smoke checks passed for all three
  measured positive feature windows and the review app's packaged assets.
- The editable local install was refreshed; it reports 0.8.0 and resolves the
  detector to this repository. Recorder settings and schedules were untouched.

`release-results.json` contains compact results, source fingerprints and all
pilot intervals. `validation.json` records commands/check counts. The full
`verified-results.json`, decoded hashes and logs are on T7 under
`analysis-results/2026-10-16-waterfowl-release/`. Source audio stays off GitHub.

From the repository root, with the T7 data and earlier frozen feature cache:

```sh
.venv/bin/python docs/evaluations/wingbeat-waterfowl-2026-10-16/verify_release.py
.venv/bin/python docs/evaluations/wingbeat-waterfowl-2026-10-16/release_summary.py
.venv/bin/python -m pytest -q
```

The verification commands rewrite derived release outputs, not audio or saved
reviews. Feature-only CI regressions use small measured fixtures; the full
original-audio verification requires the private local collection.
