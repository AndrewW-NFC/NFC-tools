"""Counterexample to a global bass requirement, not a proposed detector change."""

import argparse
import json
import runpy
from pathlib import Path

from nfc_tools.analyzers import wingbeat_accompaniment as a

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("results", type=Path)
args = parser.parse_args()
rows = json.loads(args.results.read_text())["recordings"]
report = {}
for group in ("diagnosis", "varied"):
    selected = [row for row in rows if row["group"] == group]
    remaining = [
        row["file"]
        for row in selected
        if any(
            window["broadband"]
            or any(
                feature["low_band_fraction"] >= a.MIN_LOW_BAND_FRACTION
                for feature in window["accompaniment"]
            )
            for window in row["accepted_windows"]
        )
    ]
    report[group] = {
        "clips": len(selected),
        "before": sum(bool(row["intervals"]) for row in selected),
        "after": len(remaining),
        "remaining": remaining,
    }
root = Path(__file__).resolve().parents[3]
controls = runpy.run_path(str(root / "tests/test_wingbeat_localized_pulses.py"))
before = after = 0
for seed in range(5):
    for center in (4000, 5000, 7200):
        features = a.accompaniment_features(controls["localized_noise"](seed, center))
        before += a.screen_accompaniment(features) is not None
        after += (
            a.screen_accompaniment(
                [f for f in features if f.low_band_fraction >= a.MIN_LOW_BAND_FRACTION]
            )
            is not None
        )
report["synthetic_positive_controls"] = {"before": before, "after": after, "total": 15}
report["decision"] = "Rejected: destroys existing no-bass localized-pulse sensitivity."
print(json.dumps(report, indent=2))
