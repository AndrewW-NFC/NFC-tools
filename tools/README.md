# Research and collection tools

Standalone support tools outside the installed application entry points. They collect or inspect research material, scan recordings with the current detector, compare feature summaries, and evaluate frozen listening reviews. Use each command's `--help` for inputs and output locations.

`wingbeat_research_scan.py` produces reference-validated feature sidecars; `analyze_wingbeat_research.py` summarizes them and `plot_wingbeat_research.py` plots distributions. Analysis/plotting additionally require pandas/matplotlib as identified in their headers; these are not core app dependencies. Audio tools rely on ffmpeg and the application's wingbeat code. `macaulay_collect.py` uses HTTPX.

[recording_collection](recording_collection/README.md) manages catalogs, archive extraction, and historical path resolution. See [the research audit](../docs/wingbeat-research-audit.md) for sidecar constraints.

## Files

| File | Purpose |
| --- | --- |
| [analyze_wingbeat_research.py](analyze_wingbeat_research.py) | Descriptive research comparison; no classifier, threshold fitting or production writes. |
| [evaluate_review_pilot.py](evaluate_review_pilot.py) | Evaluate the current wingbeat detector on a frozen listening-review snapshot. |
| [macaulay_collect.py](macaulay_collect.py) | Conservative, export-first Macaulay research collector (see docs/macaulay-collector.md). |
| [plot_wingbeat_research.py](plot_wingbeat_research.py) | Plot descriptive recording-level feature ECDFs; requires matplotlib/pandas/NumPy. |
| [test_relaxed_wingbeats.py](test_relaxed_wingbeats.py) | Offline sensitivity test; never changes production thresholds or results. |
| [wingbeat_research_scan.py](wingbeat_research_scan.py) | Research-only sidecar. Production decisions are never modified. See docs/wingbeat-research-audit.md. |
