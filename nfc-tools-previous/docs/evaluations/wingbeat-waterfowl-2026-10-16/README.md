> **Release follow-up:** This page describes the earlier exploratory pass before
> the October 16 release change. See [release results](release-report.md) for the
> shipped rules and fresh streaming verification. Reproducing the earlier
> baseline requires analyzer sources from commit `330e52b`; running its exploratory
> scripts against the changed analyzer will intentionally fail historical-baseline
> assertions. Frozen measurements remain on the T7.

# Waterfowl pilot diagnostic, October 16, 2026

The production detector is unchanged. Nine experimental alternatives were assessed on the 18-recording pilot comparison and 225 existing regression recordings. The broadest useful relaxation doubles passage overlap (4/12 to 8/12), but adds two flagged XC negatives and 370.4 seconds of environmental detections. A more selective spectral relaxation recovers one extra passage with 2.75 seconds of added environmental detections. It remains a research candidate, not a deployed improvement.

Full report and machine-readable results:
`/Volumes/T7/Wingbeats detector/analysis-results/2026-10-16-waterfowl-diagnostics/`

The target is mechanical wing sounds for listener review, including wings striking water. No new sound categories are required. `training-manifest.json` preserves original labels while excluding Mute Swan, Wood Duck and Cinnamon Teal from negative training. Three remaining none-heard examples are listener negatives, not guaranteed absence of faint wing sounds. The manifest assigns the pilot to development only and does not authorize a holdout claim.

## Reproduction

Run from the repository root with the T7 connected. These commands recompute derived feature/output files, never annotations or source audio. Preserve the original output before a rerun. The fixed root in rescore.py and summarize.py is intentional for this dated experiment; update it when reproducing into a different destination.

```sh
.venv/bin/python docs/evaluations/wingbeat-waterfowl-2026-10-16/experiment.py pilot '/Volumes/T7/Wingbeats detector/analysis-results/2026-10-16-waterfowl-diagnostics/features'
.venv/bin/python docs/evaluations/wingbeat-waterfowl-2026-10-16/experiment.py controls '/Volumes/T7/Wingbeats detector/analysis-results/2026-10-16-waterfowl-diagnostics/features'
.venv/bin/python docs/evaluations/wingbeat-waterfowl-2026-10-16/rescore.py
.venv/bin/python docs/evaluations/wingbeat-waterfowl-2026-10-16/summarize.py
```

The pilot uses the frozen review snapshot from the preceding evaluation. Originals are extracted to temporary files, hash checked and decoded to 24 kHz mono using the production FFmpeg convention. Only derived measurements and results persist. Source hashes and intervals for all 225 controls match the prior October 13 experiment. Pilot features match all 18 original production comparisons. Candidate gate changes are applied to cached measurements; production modules are never monkey-patched or modified.

The report is a curated interpretation of `candidate-results.json` and `miss-diagnostics.json`. Source fingerprints and validation counts are in `provenance.json`. `candidate-disagreements.json` lists the three environmental intervals requiring adjudication before the narrow candidate could be promoted.

Validation: 172 existing tests in `test_wingbeat_upper_interference.py`, `test_wingbeat_localized_pulses.py`, and `test_wingbeat_spectral_support.py` passed. These tests validate the unchanged production implementation; baseline reconstruction and source/PCM hashes validate the experimental measurement pipeline. No independent holdout, full-night rescan, or gain/alignment sweep was performed in this experiment.

Label-scope caution: negative labels are inherited from the older experiment. The three new environmental intervals for the narrow candidate lie outside the original highlighted listening intervals. Their added duration measures review workload, not confirmed false-positive duration. `candidate-disagreements.json` preserves those original intervals and source metadata categories.
