# Developer checks and evaluations

Commands for repository consistency checks and focused wingbeat diagnostics. Run them from the repository root with the development environment active.

`python scripts/check_versions.py` checks release declarations. `python scripts/check_dependencies.py` compares dependency manifests and needs Python 3.11+. Evaluation and benchmark scripts accept `--help`; they use the installed `nfc_tools` package, ffmpeg, and (where imported) NumPy. Audio evaluation requires explicit input recordings; measured tuning results are not field-accuracy estimates.

## Files

| File | Purpose |
| --- | --- |
| [benchmark_wingbeats.py](benchmark_wingbeats.py) | Compare cached/uncached screening on identical decoded PCM without publishing results. |
| [check_dependencies.py](check_dependencies.py) | Compare package dependency names across manifests (requires Python 3.11+). |
| [check_versions.py](check_versions.py) | Check the four release version declarations without extra dependencies. |
| [evaluate_wingbeat_negatives.py](evaluate_wingbeat_negatives.py) | Compare the original, cross-band and current screens on labeled audio clips. |
| [evaluate_wingbeats.py](evaluate_wingbeats.py) | Offline diagnostic sweep; synthetic results do not estimate field accuracy. |
