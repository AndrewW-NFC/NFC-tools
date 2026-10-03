# WING research handoff bundle

This folder preserves the handoff documents for the NFC Tools WING research-instrumentation project. As of September 26, 2026, the data and original root handoff ZIP have moved out of the current source tree; the data is available as a release asset. Normal application use and tests do not require it.

## Contents

The documents and scanner remain in Git. The three `data/` files are optional downloads from the [research-data release](https://github.com/AndrewW-NFC/NFC-tools/releases/tag/wingbeat-research-data-2026-09-26).

- `CODEX_PROMPT.md` — detailed task prompt for Desktop Codex
- `STATE_OF_WORK.md` — concise status and experimental cautions
- `FEATURE_DICTIONARY.md` — fields emitted by the research instrumentation
- `tools/wingbeat_research_scan.py` — original handoff scanner, retained for provenance; use the integrated repository scanner at [`../../tools/wingbeat_research_scan.py`](../../tools/wingbeat_research_scan.py) for current research
- `data/fsd50k_wing_scan_dev.csv` — first-pass WING scan of all 40,966 FSD50K development files
- `data/xc_wingbeat_research_files.csv` — per-recording results from 958 xeno-canto wingbeat-containing recordings
- `data/xc_wingbeat_research_windows.csv.gz` — instrumented per-window xeno-canto results

## Restore the research data

Download [wingbeat-research-data-2026-09-26.zip](https://github.com/AndrewW-NFC/NFC-tools/releases/download/wingbeat-research-data-2026-09-26/wingbeat-research-data-2026-09-26.zip) into this folder, or run from the repository root:

```bash
gh release download wingbeat-research-data-2026-09-26 --repo AndrewW-NFC/NFC-tools --pattern '*.zip' --dir research/wingbeat_research_codex_bundle
```

Verify the archive SHA-256 before extracting it. Run this Python code from the repository root:

```python
from pathlib import Path
import hashlib
import zipfile

bundle = Path("research/wingbeat_research_codex_bundle")
archive = bundle / "wingbeat-research-data-2026-09-26.zip"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == "4cbf5b77abfc1d0dea74c86827380423635a24eee73c0223ec1ef14a75bbb927"
with zipfile.ZipFile(archive) as data:
    data.extractall(bundle)
for line in (bundle / "SHA256SUMS.txt").read_text().splitlines():
    expected, name = line.split("  ", 1)
    assert hashlib.sha256((bundle / name).read_bytes()).hexdigest() == expected, name
```

This restores the original `data/` paths used by the research commands. Restored data and downloaded archives are ignored by Git. The data files are byte-for-byte unchanged; prior Git history is retained.

`CODEX_PROMPT.md` and `STATE_OF_WORK.md` preserve the original handoff context. For the integrated tooling, follow [the research audit](../../docs/wingbeat-research-audit.md). Do not merge the bundled scanner into production WING blindly.
