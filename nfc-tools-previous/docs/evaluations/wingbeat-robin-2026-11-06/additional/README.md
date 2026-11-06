# Additional robin and likely-footstep baseline — November 6, 2026

All 11 supplied clips reproduce WING detections in the unchanged detector.
The archive folder labels and user's description define the two categories;
“likely footsteps on leaves” remains tentative, not independently confirmed.

| User-labeled category | Clips | Duration | Clips flagged | Accepted windows |
|---|---:|---:|---:|---:|
| Robin misidentified as WING | 9 | 91.39 s | 9 | 32 |
| Neither robin nor WING; likely footsteps | 2 | 20.39 s | 2 | 3 |

All accepted windows use spectral accompaniment. None passes the broadband
route; none requires the irregular-rhythm alternative. Of the 32 robin windows,
24 use localized-lobe support and eight use spectral support. Tracked residual
centers span approximately 2.55–4.71 kHz. This confirms the earlier diagnosis
that both acceptance mechanisms are implicated; suppressing only thin tonal
calls would leave most of these accepted windows.

Both likely-footstep clips use localized-lobe support in the 6–9.5 kHz search
band, with tracked residual centers near 6.73–6.75 kHz. Clip 10 is flagged at
4.00–6.25 s; clip 11 at 4.00–6.00 s. They belong in a separate negative category,
not in the robin-specific pattern. A robin rejection rule alone need not
eliminate this different sound source.

Every robin detection starts at 4.00 s in its supplied crop. Endpoints are in
`clips.csv`; these are detector intervals, not human-annotated call boundaries.

## Evaluation scope

This is a baseline on additional examples, not a before/after test of a fix.
There is no frozen candidate robin-rejection rule, and no thresholds were tuned
against this archive. These clips have now been inspected; if they are the
previously held-back examples, any later tuning informed by these measurements
must not be presented as an untouched holdout evaluation.

No exact accepted-window PCM hashes match the earlier training archive or other
clips within this archive. This limited check does not establish independent
recording sessions or rule out overlap outside accepted windows. Filenames
are preserved with folder paths so identically numbered clips from different
archives cannot be confused. Original audio is unmodified and not in the repo.

## Verification and reproduction

The diagnostic script uses production FFmpeg decoding and the complete
production streaming schedule, then independently reconstructs merged intervals
from its accepted windows and asserts agreement with `detect_stream` for every
clip. All 11 comparisons passed. Python F checks and diff-whitespace checks
passed. Production detector code remains unchanged.

`results.json` records source/archive hashes, detector revision, per-window
features and detection intervals. `training-overlap.json` records the limited
cross-archive overlap check. Reproduce from the repository root:

```sh
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-06/diagnose.py '/path/to/Test against.zip' --layout additional --output /tmp/robin-additional-baseline
```

Current extracted audio location: `/Volumes/T7/Wingbeats detector/audio-library/robin-training/`
(the additional set is under `Test against/`). The ZIP commands above describe
the original input; use the exclusion report’s verifier for the current layout.
