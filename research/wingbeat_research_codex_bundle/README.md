# WING research handoff bundle

This folder is a handoff for the NFC Tools WING research-instrumentation project.

## Contents

- `CODEX_PROMPT.md` — detailed task prompt for Desktop Codex
- `STATE_OF_WORK.md` — concise status and experimental cautions
- `FEATURE_DICTIONARY.md` — fields emitted by the research instrumentation
- `tools/wingbeat_research_scan.py` — research-only scanner developed against the current WING implementation
- `data/fsd50k_wing_scan_dev.csv` — first-pass WING scan of all 40,966 FSD50K development files
- `data/xc_wingbeat_research_files.csv` — per-recording results from 958 xeno-canto wingbeat-containing recordings
- `data/xc_wingbeat_research_windows.csv.gz` — instrumented per-window xeno-canto results

## Recommended use

Place the ZIP in the root of the `nfc-tools` repository. Give Desktop Codex the text in `CODEX_PROMPT.md`. Let Codex inspect/unpack the bundle and decide the best repository location for research-only tooling. Do not merge the scanner into production WING blindly.
