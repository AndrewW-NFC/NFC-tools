# Targeted upper-frequency WING interference filter — October 13, 2026

## Decision and scope

Add a narrow rejection condition to the localized-pulse acceptance alternative.
The supplied user-labeled insect clip has an upper spectral peak at 8.53 kHz,
but its accepted accompaniment windows track a weaker 6.68–6.94 kHz lobe.
Those pulses closely follow the much stronger 8–9.5 kHz component, while the
3.5–6.5 kHz envelope has little correlation with them. A peak-frequency cutoff
alone would miss this mechanism and risk excluding genuine high wing sounds.

Reject **only localized-pulse support for that band** when all of these hold:

- Tracked median maximum is at least 6.5 kHz and below 8 kHz.
- Pulse-linked excess power in 8–9.5 kHz is at least three times that in
  6.5–8 kHz. Both comparison bands are 1.5 kHz wide.
- The detrended 8–9.5 kHz amplitude envelope correlates with the tracked
  pulse envelope by at least 0.90.
- Its pulse-on versus pulse-off amplitude contrast is at least 0.70.
- The detrended 3.5–6.5 kHz envelope correlates with those pulses by less
  than 0.30. Unrelated lower-frequency energy does not supply pulse support.

These use the existing top/bottom-quartile pulse masks and temporal smoothing.
Excess power is the nonnegative per-bin difference of mean on/off power.
Contrast is `(mean_on - mean_off) / mean_on`. Correlations are mean-centered.
No audio is filtered or modified. The original whistle/spectral alternative,
broadband screen, other independently accepted bands, window schedules and
scores are unchanged. A candidate can remain if any unaffected route accepts it.
The research sidecar exports the four measurements and rejection reason.

The thresholds were selected using this insect clip. They are provisional
engineering choices, not validated biological boundaries or insect identification.
The earlier high-frequency Muscovy Duck and Red-necked Woodpecker examples remain
important counterexamples to a blanket frequency exclusion.

## Recorded evaluation

The original sample changes from two intervals, **4–7.25 s and 7.5–9.75 s**,
to **no detections**. All eleven previously accepted analysis windows lose only
their localized-pulse support. Across those windows the upper/middle excess
power ratio is 4.82–11.66, upper coherence 0.972–0.995, upper contrast
0.870–0.933, and lower coherence −0.041–0.195.

| Sample set | Before | After |
|---|---:|---:|
| Supplied insect: 12 gain/alignment combinations | 12/12 | 0/12 |
| Confirmed XC passages overlapped | 44/76 | 44/76 |
| Confirmed XC annotated seconds covered | 168.75 | 168.75 |
| Confirmed species references | 10/11 | 10/11 |
| Three confirmed field passages × 12 variants | 36/36 | 36/36 |
| Reviewed XC negatives flagged | 3/23 | 3/23 |
| Reviewed environmental negatives flagged | 100/100 | 100/100 |
| Separate discrete-sound negatives flagged | 0/11 | 0/11 |

All **257 non-insect evaluation jobs retain exactly the same intervals**.
In the 76 XC positives, 45 recordings contain some detection but only 44 overlap
the confirmed annotation; the table uses annotation overlap. Bufflehead remains
the reference-set miss. Both high-frequency XC examples retain their baseline
outputs; their annotated passages remain existing misses, so they do not provide
positive recovery evidence for this filter. The broader reviewed negatives show
no improvement: the supported claim is suppression of the supplied insect pattern,
not a general improvement across all environmental sounds.

The 199 reviewed XC/environmental recordings use the existing definite labels;
uncertain labels remain excluded. All reconstructed baseline intervals and
freshly decoded PCM hashes are checked against the October 11 production run.
For changed recordings and all field/reference/insect/discrete controls, the
comparison also checks the new intervals against actual `detect_stream` output.
The before/after comparison disables only the new veto for its baseline.

The insect variants use gains 0.1, 1 and 3 crossed with leading silence of
0, 0.25, 0.5 and 0.75 seconds. The three field neighborhoods are 1078–1089,
1488–1493 and 2520–2530 seconds in the October 11 03:00 source recording, each
with the same twelve transformations. Variants are correlated regression checks,
not additional independent observations. Field testing here uses those crops,
not a new full-hour scan. The filter can only remove acceptance, so it cannot
introduce new full-hour candidates through unchanged routes.

The environmental sample was selected from prior detections. It does not
estimate general environmental false-positive rates. This evaluation checks
regression on an already studied collection; it is not an independent holdout.
A genuine wing sound sharing this full pattern could still be suppressed.
Additional independently labeled insects and wingbeats are needed to establish
how broadly the improvement transfers to new nights.

## Tests and evidence

- Full suite: 918 passed, 3 platform skips (collected before the final seven
  targeted controls were added).
- Final targeted file: 34 passed. Controls cover prior false acceptance,
  gain changes, window offsets, synchronized lower support, independent upper
  rhythm, dominant 8.5 kHz wing-like lobes, the existing spectral alternative,
  overlapping broadband wing pulses and research diagnostics.
- Final combined interference/research checks: 94 passed.
- Existing localized-pulse and accompaniment tests: 149 passed.
- Analyzer/new-file lint, research F checks, version/dependency consistency,
  and diff whitespace checks passed.

The full suite includes unrelated pre-existing local Macaulay tests; those files
are not part of this change. No supplied audio is committed.

[Summary](summary.json), [per-recording results and decoded hashes](recordings.csv),
and [source/output fingerprints](provenance.json) accompany this report.
Detailed changed-window features remain on T7 in
`/Volumes/T7/Wingbeats detector/Insect filter 2026-10-13/results.json`.

Reproduce from the repository root with the editable package installed:

```sh
.venv/bin/python docs/evaluations/wingbeat-insect-2026-10-13/evaluate.py \
  '/Volumes/T7/Wingbeats detector/Detector comparison 2026-10-11/Improvement experiment/partition.json' \
  '/Volumes/T7/Wingbeats detector/Insect filter 2026-10-13' \
  --sample '/Volumes/T7/NFC recordings/2026-10-12/audio/clips/18-36-09/WING (review required)-Wingbeats 3.wav' \
  --references '/Volumes/T7/Wingbeats detector/Confirmed species wing sounds' \
  --negatives '/Volumes/T7/Wingbeats detector/wav files with false positive WING sounds.zip' \
  --field '/Volumes/T7/NFC recordings/2026-10-10/audio/012_NFC_2026-10-11_03-00-00.wav'
.venv/bin/python docs/evaluations/wingbeat-insect-2026-10-13/summarize.py \
  '/Volumes/T7/Wingbeats detector/Insect filter 2026-10-13/results.json' \
  '/Volumes/T7/Wingbeats detector/Detector comparison 2026-10-11/Improvement experiment/production_verification.json' \
  docs/evaluations/wingbeat-insect-2026-10-13
.venv/bin/python -m pytest tests/test_wingbeat_upper_interference.py -q
```
