# October 16, 2026 — wingbeat collection, annotation and detector work

> Historical work summary. Version numbers and local installation instructions below describe October 16, 2026; see the current [developer notes](../../README_DEV.md) for setup instructions.

## Collection organization

Organized the Macaulay delivery into an indexed archive of 3,587 recordings,
including 607 waterfowl/Anatidae recordings. WAV names include the common name
and stable ML catalog identifier. Retained original deliveries and source
metadata, with migration maps for renamed paths.

Separated the T7 workspace into `audio-library/`, `catalogs/`, `reviews/`,
`analysis-results/`, `tools/`, and `archive/`, with a root guide. Archived 17 old
scripts as reference-only text. Replaced 494 checksum-identical review copies
with links to their originals, reclaiming about 1.01 GB. Removed obsolete root
shortcuts and updated live references. The cleanup audit resolved 4,330 distinct
absolute references and 252 local listening links without errors. Original
snapshots and the detailed audit remain under the T7 change-history archive.

Verified the Central European Birds source archive and filed it as ready to
import; its audio has not been imported. The repository now includes source
copies of the recording-listing/extraction, old-path resolution and reference
checking tools under `tools/recording_collection/`. Audio assets and large
collection indexes remain on T7 rather than in Git.

## Listening and annotation

Built a local waterfowl review app with playback, waveform seeking, passage
boundaries, confidence, notes, listened coverage, completion checks, autosave,
conflict detection, SQLite revision history, per-save JSON backups and exports.
Prepared 20 recordings spanning 20 species and 20 recordists, totaling 8.4 minutes.
Andrew completed all 20. The pilot contains 12 clear passages totaling 74 seconds,
plus faint/uncertain findings and listener-negative examples.

Kept one broad screening target: mechanical wing sounds, including wings
striking water. No additional behavior categories were added. Mute Swan, Wood
Duck and Cinnamon Teal are excluded from negative training. The saved development
manifest permits the 12 clear-positive recordings and three remaining
listener-negative recordings, while preserving the caveat that faint sounds
could escape listening. No training was performed and no independent test-set
claim is made.

## Detector evaluation and update

Measured the prior detector at 4/12 clear-passage overlaps and 6.25/74 seconds
covered. Investigated the eight misses using frozen per-window measurements and
compared nine initial alternatives with 225 prior reference/control recordings.
A general rhythm relaxation recovered more passages but substantially increased
review workload, so it was not adopted.

The shipped follow-up instead adds a guarded less-regular-pulse route requiring
strong distributed spectral excess, accompanying noise, bass and lower-band
synchrony. It recovers the marked Mallard and Common Merganser passages. A separate
conditional spectral-flatness allowance recovers Pacific Black Duck. Existing
acceptance routes and upper-interference protection remain in place. These are
heuristic improvements, not a newly trained statistical model.

See [release results](../evaluations/wingbeat-waterfowl-2026-10-16/release-report.md)
for exact detection intervals, coverage, control-set tradeoffs and fresh streaming
verification. Additional detections outside earlier highlighted listening regions
are review workload, not automatically confirmed false positives. The new rules
remain experimental and do not establish general field accuracy.

## Tonight's local installation

The editable environment at `/Users/andrewwhitacre/Desktop/nfc-tools/.venv` was
refreshed to the current 0.8.0 package metadata and uses this checkout's detector.
No recorder settings or schedules were changed. Start a fresh app process from
this checkout before tonight's session:

```sh
cd /Users/andrewwhitacre/Desktop/nfc-tools
.venv/bin/nfc-tools
```

The annotation app at port 8877 is separate from the recording app at port 8765.
The GitHub update contains source, tests, documentation and compact evaluation
results, not the 60 GB archive or recording audio. Existing unrelated Macaulay
collector work was left untouched.
