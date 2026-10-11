# Brief WING accompaniment windows — October 11, 2026

The adopted change adds a complete **one-second accompaniment window every
250 ms**, using the existing strict rhythm, pulse-count, synchrony, and spectral
checks. All original windows and thresholds remain in place. Previously found
intervals cannot be removed by this additive pass. The broadband screen and the
conditional relaxed rhythm route are not used on the new windows. Audio stays
bounded to the existing two-second stream buffer.

On the user's reviewed XC set, this finds **44 of 76 confirmed wingbeat passages,
up from 40**. It adds **14 seconds** of false-alarm time across the reviewed
negatives, without flagging any additional negative files. This is a modest
sensitivity improvement for a listening aid. It does not solve environmental
false alarms, identify species, or establish general field accuracy.

## Measured annotation results

| Measure | Before | After |
|---|---:|---:|
| Confirmed passages with any overlap | 40/76 | 44/76 |
| Passages with at least 50% timestamp coverage | 31/76 | 33/76 |
| Passages with at least 90% timestamp coverage | 11/76 | 13/76 |
| Annotated wingbeat seconds covered | 162/365.5 | 168.75/365.5 |
| XC recordings labeled No that trigger | 3/23 | 3/23 |
| Reviewed environmental negatives that trigger | 100/100 | 100/100 |
| Total flagged seconds in those 123 negative files | 1279.973 | 1293.973 |

The environmental sample was selected from detector hits, so its 100/100 result
is **not** an estimate of the detector's false-positive rate on environmental
audio generally. The XC review sample was also deliberately selected, rather
than a representative random sample. The 51 Uncertain XC labels are excluded.
The user's confirmations apply to the 100 reviewed environmental recordings;
no unreviewed environmental recordings were relabeled.

### Newly overlapping confirmed passages

Times are elapsed seconds in the source recording. Species names are source
metadata, not an acoustic identification by this detector.

| Review ID / file | Reported species | User interval | New detector interval(s) |
|---|---|---|---|
| XC-019 / XC1084347.wav | Common Wood Pigeon | 1–4 | 1.75–2.75 |
| XC-026 / XC1136070.mp3 | Rock Dove | 0–10 | 6.75–7.75 |
| XC-036 / XC1164050.wav | Common Wood Pigeon | 1–2 | 0.25–1.25; 1.5–2.5 |
| XC-092 / XC752650.mp3 | Black-throated Loon | 0–4 | 0.25–1.75 |

An overlap does not mean the entire annotated passage is recovered. The result
still misses 32 confirmed passages entirely.

## Selection and limitations

Before scoring variants, the 199 definite-label recordings were grouped by XC
recordist or environmental uploader. A fixed SHA-256 rule assigned groups to
development or an internal validation subset (see external `partition.json`).
Development contained 56 positives and 106 negatives; validation contained
20 positives and 17 negatives, with only one XC negative.

The initial experiments tested shorter windows and upper bounds on residual
pulse contrast. A combined candidate selected on development retained all
positive events, gained four, and reduced negative flagged time. On internal
validation it retained the same 14 detected events, reduced false-alarm time,
and lost 1.5 seconds of positive coverage. More importantly, the contrast cap
rejected **10 of 20** existing synthetic positive whistle-with-synchronous-noise
controls. That cap was rejected and is **not** in production.

The retained shorter-window change was then evaluated separately. It gains
four positive events on development (26→30/56); the internal validation event
count is unchanged (14/20), with positive coverage increasing 60.75→62.75 s.
False-alarm time increases by 11.25 s and 2.75 s respectively. This is an
exploratory follow-up after inspecting the combined candidate's results. The
collection was already examined during the earlier diagnostic work, so neither
subset is a pristine independent test. No fresh independent field accuracy
claim is made.

## Field and control checks

The full 3600-second field recording retains exactly the same three intervals:
17:59.25–18:07.25, 24:49.50–24:51.00, and 42:04.50–42:07.25.
There are no newly flagged intervals elsewhere in that hour.

- Confirmed-species reference clips: 10/11 detected before and after. Bufflehead
  remains missed. The green-winged teal clip gains 3.25–4.25 s in addition to
  its existing intervals; that clip is labeled as containing wing sounds
  throughout, rather than having a newly independently adjudicated passage.
- Separate discrete-sound negatives: 0/11 before and after.
- All 36 gain/alignment variants of the three field passages retain detection.
  These correlated transformations are regression checks, not independent data.
- The new pass rejects all 125 tested synthetic negative signals: tones,
  harmonics, sweeps, and unrelated stationary/shaped noise. Every eligible
  one-second window at the 250-ms hop was checked.

All **199** freshly decoded production outputs exactly match the cached
predictions, and their decoded audio hashes match the feature cache. The full
suite passed **877 tests**, with 3 platform skips; 95 targeted tests also passed.
Ruff F checks, compilation, version consistency, dependency consistency, and
diff whitespace checks passed. Source hashes and totals are in `summary.json`.
The new pass requires additional feature calculations; no runtime speedup is
claimed. Existing exported detector results are historical and are not silently
overwritten by changing the code.

## Reproduction and evidence

Baseline Git revision: `88d852201a9c976f611a33567057800b10858e0f`.

Full local experiment:
`/Volumes/T7/Wingbeats detector/Detector comparison 2026-10-11/Improvement experiment/`.
It contains feature caches, frozen grouping, all development variants,
`selected_candidate.json`, `validation_results.json`, `short_only_results.json`,
field PCM hashes and comparisons, control results, and real production output
verification. The original labels and audio are preserved.

The external `cache_features.py` requires the baseline source hashes from the
original scan and must be run against that revision. `evaluate.py`,
`select_candidate.py`, `validate_candidate.py`, and `check_short.py` reproduce
selection and cached comparisons. They live beside the cache and partition.
The `.npz` caches include baseline decisions; the vectorized evaluator asserts
exact agreement with those decisions before evaluating a variant.

This folder contains:

- `candidate.py`: the rejected contrast-cap prototype, explicitly separate from
  production. Its iterator filters the later production brief pass to reproduce
  the original schedule before inserting the candidate's one-second windows.
- `run.py`: complete decoded field comparison of that rejected prototype.
- `run_short.py`: the added one-second pass alone, using the same field CLI.
  Its `after` array contains only short-pass hits. Those hits are merged with
  the earlier saved production intervals **after matching every PCM SHA-256**;
  the merged result is external `short-field-comparison.json`.
- `check_controls.py` and `check_short_controls.py`: deterministic positive and
  negative signal controls.
- `verify_production.py`: decode all 199 annotated recordings and assert exact
  agreement between actual production intervals and cached predictions.

For example, from the repository root:

```sh
.venv/bin/python docs/evaluations/wingbeat-annotation-candidate-2026-10-11/verify_production.py \
  '/Volumes/T7/Wingbeats detector/Detector comparison 2026-10-11/Improvement experiment'
.venv/bin/python -m pytest -q
```

Further substantial improvement needs features or a learned model that
separate genuine wing pulses from environmental pulse trains, evaluated on
fresh, independently labeled recordings. The rejected cap demonstrates why
reducing false alarms by tightening a single descriptive feature is unsafe.
