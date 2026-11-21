# Stronger-sweep robin rejection — November 21, 2026

Five user-labeled robin false-positive clips were supplied (numbered 3–7).
A limited extension of the existing call-motion veto removes all detections
from clip 6 and one interval each from clips 4 and 5. Clips 3 and 7 are unchanged.
Four of five supplied clips still trigger; this is a partial fix, not robin
recognition or a general accuracy estimate.

## Fresh results at original gain and alignment

Times are seconds relative to each supplied file.

| Clip | Before | After |
| --- | --- | --- |
| 3 | 4.00–5.75 | 4.00–5.75 |
| 4 | 4.00–6.00; 8.25–9.25 | 8.25–9.25 |
| 5 | 0.25–1.75; 4.00–5.00 | 4.00–5.00 |
| 6 | 4.00–5.50 | None |
| 7 | 4.00–5.50 | 4.00–5.50 |

Clips 4 and 5 overlap: clip 5 begins 4.25 seconds into clip 4. Their
24 kHz decoded samples match exactly throughout the overlap excluding 10 ms
at each edge, where separate resampling can differ. These are not independent
examples. All five are development inputs used to investigate the adjustment.
The user supplied their robin labels; the detector does not identify species.

## Change and rejected alternative

The original veto requires less than 0.05% low-band energy, at least 700 Hz
centroid excursion, and at most 0.80 instantaneous/aggregate bandwidth ratio.
It remains unchanged. A second branch allows less than 0.1% low-band energy
only when excursion is at least 1,000 Hz, retaining the same width-ratio gate.
The low-band fraction compares 150–600 Hz with 150–3,000 Hz; it is not a fraction
of all recorded sound. Measurements otherwise follow the
[November 6 implementation](../wingbeat-robin-2026-11-06/exclusion/README.md).

Simply raising the original bass guard to 0.1% rejected the measured genuine
field window `field-1078-1-0:1.25:3500` (about 724 Hz excursion). That alternative
was discarded. The stronger-sweep branch preserves that regression while
rejecting some newly supplied sounds with excursions above 1,000 Hz. The new
cutoff is a provisional engineering choice selected using these examples,
not a validated boundary between calls and mechanical wing sounds.

The short-frame motion transform is now computed for otherwise eligible
accompaniment bands below the 0.1% bass guard and is shared within each window.
Broadband acceptance remains independent. No gate requires a quiet beginning,
quiet ending, or a smooth flyby envelope. No runtime benchmark was performed.

## Validation and limits

Gains 0.1, 1, and 3 were crossed with leading silence of 0, 0.125, 0.5, and
0.75 seconds. Float PCM variants were not clipped. There were 240 streaming
runs: before/after for 120 correlated variants across ten input recordings.

| Group | Variants | Flagged before | Flagged after | Changed results |
| --- | ---: | ---: | ---: | ---: |
| Five supplied robin clips | 60 | 60 | 48 | 30 |
| Four genuine-wingbeat controls | 48 | 42 | 42 | 0 |
| Mute Swan background control | 12 | 0 | 0 | 0 |

Clip 6 loses all 12 variant detections; clips 4 and 5 change in nine variants
each. Other negative variants retain their baseline results. All positive
intervals and scores remain identical, including existing misses. Controls
are the supplied abrupt-start clip, Mute Swan wings, and both November 10
reported-miss fixtures. This does not establish retention on other recordings.
The earlier 243-recording T7 corpus was unavailable and was not rerun.

The wingbeat pytest run passed **654 tests with six known expected failures**
(the existing alignment-sensitive second November 10 crop). New regression
checks reproduce the robin false positive with only the new branch disabled,
verify gain robustness and cached/uncached agreement, retain abrupt wingbeats,
and protect the measured field window that rejected the broader adjustment.
Python F checks and diff whitespace checks passed.

The supplied abrupt-start clip continues to return 4.00–6.00 s. A PCM16 fixture
cropped to that interval alone still returns 0.00–2.00 s. House obstruction is
the user's proposed explanation; it is not established by these tests.

## Evidence and reproduction

`baseline-features.json` records source paths, SHA-256 hashes, original
intervals and accepted-window features, including unconditionally computed
motion diagnostics. `results.json` records all variant intervals and scores.
The baseline is revision `cd1f097af68f3ef24ff8aa9665d4d8b5b7261607`; results were
measured with the candidate rule substituted in memory, then checked against
its production implementation at original gain/alignment. Original audio files
were unchanged. Compact PCM16 crops and provenance are in `tests/fixtures/`.

From the repository root, with the source paths in the manifest available:

```sh
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-21/verify.py --output /tmp/robin-20261121-recheck.json
.venv/bin/python -m pytest -q tests/test_wingbeat_robin_strong_sweep.py tests/test_wingbeat*.py
```

The verifier restores the prior veto in memory for its baseline and retains
all other current screening behavior. Existing exports are not reanalyzed,
and running or packaged applications are not restarted or rebuilt by this
source change. Remaining robin triggers need further investigation with more
labeled recordings and broader positive retention validation.
