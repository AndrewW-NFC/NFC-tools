# Robin false triggers and obstructed wingbeat passages

Requested November 21, 2026. Robin false positives are a user-reported bug,
eligible for investigation during the project hold. Additional validation of
obstructed passages is recorded for the January 10, 2027 revisit. The initial
inspection changed no detector rules. After the user supplied five new robin
examples, a limited stronger-sweep rejection fix was implemented; see the
[follow-up evaluation](../evaluations/wingbeat-robin-2026-11-21/README.md).

## Robin calls

The user requests fewer American robin calls triggering WING. Production already
contains `swept_call_interference` in `wingbeat_accompaniment.py`. The
[November 6 evaluation](../evaluations/wingbeat-robin-2026-11-06/exclusion/README.md)
records a reduction from nine to three flagged additional robin clips. These
are previously inspected development examples, not independent accuracy data.
The evaluation also records genuine-wingbeat losses from less guarded rules.

The earlier audio location,
`/Volumes/T7/Wingbeats detector/audio-library/robin-training/`, was unavailable
during this inspection. The user subsequently supplied clips numbered 3–7 from
the November 20 morning recording and identified their sounds as robin false
positives. These enabled the follow-up fix; the older T7 corpus remains
unavailable. The supplied abrupt-start wingbeat example is a positive control,
not a robin negative. Residual robin detections remain unresolved.

## House obstruction and abrupt passage boundaries

The user reports that a bird flying perpendicular to the house may become
audible suddenly when its sound path clears the side of the house, or disappear
while still loud. Preserve sensitivity to passages starting or ending near peak
volume. The house-obstruction explanation is the user's hypothesis, not a
cause established from this audio analysis.

Source: `/Users/andrewwhitacre/Desktop/WING (review required)-Wingbeats_03.wav`.
SHA-256: `3744b5ce922c2009b6378e7b3a73a25c2e66fab84769fab20fd08e48c03d3c98`.
The file is mono 48 kHz float PCM, decoded using the production FFmpeg path to
mono 24 kHz float PCM for screening. Duration: 10.069333 seconds. The original
was not changed or copied into the repository.

At source revision `cd1f097af68f3ef24ff8aa9665d4d8b5b7261607`, fresh
`detect_stream` runs returned:

| Input interval from original clip | Detection relative to input |
| --- | --- |
| Full clip | 4.00–6.00 s |
| 4.00 s to end | 0.00–2.00 s |
| Start to 6.00 s | 4.00–6.00 s |
| 4.00–6.00 s only | 0.00–2.00 s |

All four runs returned periodicity 0.7413739618549513. Crops were made in
memory after decoding, with sample indices rounded at 24 kHz. These checks
show that the detected interval does not need surrounding quiet context in
this example. They do not prove that all audible wingbeats were captured,
identify the source independently, or simulate every physical obstruction.

Code inspection found no smooth whole-passage rise/fall requirement. Broadband
screening removes slow envelope trends before rhythm/coherence checks;
accompaniment screening measures repeated local pulses. `distinct_pulses`
allows above-threshold regions touching the start or end of a window. Minimum
duration, pulse count, contrast, frequency evidence, and window alignment can
still cause misses when a passage is shortened.

Validation: `pytest -q tests/test_wingbeat_call_motion.py
tests/test_wingbeat_brief.py` passed all 52 tests. This checks current software
behavior, not field performance. Reviewed README.md, README_DEV.md, and
README_WINGBEATS.md and clarified the applicable limitations in each.

## Deferred validation

At the January revisit, include manually annotated passages with sudden starts,
sudden endings, and both boundaries near peak volume. Compare detection coverage
as well as file-level hits, retain this example, and check several window
alignments and gains. Evaluate robin negatives alongside these positives so
call suppression does not inadvertently require a smooth flyby envelope.
Include representative reviewed nights, analyzer comparisons, detection
quality, processing time, and human review workload in the field baseline.
