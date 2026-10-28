# Mute Swan missed-passage regression, October 28, 2026

The user identified wingbeats at 10–19 seconds in `Untitled 1.wav`, a 28.27-second
48 kHz stereo float WAV also containing three vocalizations. The original
production detector returned no candidates after its normal 24 kHz mono decode.

## Diagnosis

The tracker chooses the strongest spectral bin in each search range, independently
per frame. In this recording stronger neighboring sounds distract the broad
1.8–4 kHz tracker from the wingbeat passage. At 14.5–16 seconds its median tracked
frequency is 1,922 Hz, repetition is 0.541, and surrounding-noise synchrony is
0.240: below the normal 0.60 and 0.40 requirements. The broadband route also fails
flatness, repetition, low-band support, and cross-band synchrony checks.

An additional interior 2.2–3.5 kHz search tracks the passage near 2,625 Hz in that
same window. Repetition is 0.803, second repetition 0.844, noise synchrony 0.712,
and pulse count five. Its prominence (16.46) and pulse-excess flatness (0.226)
meet the existing conditional spectral-support route. No thresholds need changing.

Initial ranking by repetition alone highlighted a separate narrow band near
3.7 kHz, present outside the user-marked passage. That is not the recovery target.
The change does not relax the checks that reject that background. Nor does it
use the presence of vocalizations as evidence of wingbeats.

## Change and validation

Add the interior search without replacing any original range or changing the
screening gates. The updated full recording produces one WING interval:
**14.25–16.75 seconds**, periodicity **0.867**. This recovers the passage for review;
the interval is not a claim to mark every audible wingbeat. The normal four-second
review padding covers 10.25–20.75 seconds.

Regression audio excerpts and source/conversion fingerprints are stored in
`tests/fixtures/mute-swan-provenance.json`. Tests compare the original search bands
with the interior band, exercise gain and window alignment, check both frame-cache
modes, and reject the separate repeating background in a 0–3 second excerpt.

The existing 578 wingbeat tests passed with the additional range, including
synthetic call-like signals, tonal leakage, insects, restricted-noise bursts,
waterfowl feature regressions and cached/uncached equivalence. Twelve new
audio-regression cases also passed. The full recording retains one flag inside
the marked passage at gains 0.1, 1 and 3, and with 70 ms and 190 ms leading offsets.
The production WAV plugin succeeds and writes one WING detection.
The full project suite passes: **1,014 passed, 3 skipped**. Targeted lint and
`git diff --check` also pass.

This recording is a development example, not independent validation. The external
T7 collection of 225 control recordings is unavailable in this session, so no new
real-corpus false-positive rate is claimed. Searching another range can increase
review workload even though all acceptance gates remain unchanged.
