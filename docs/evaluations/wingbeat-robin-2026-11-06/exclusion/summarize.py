"""Write compact results from completed fresh-stream comparisons."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--field-results", type=Path, required=True)
parser.add_argument("--supplied-results", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
field = [json.loads(p.read_text()) for p in sorted(args.field_results.glob("*.json"))]
supplied = [
    json.loads(p.read_text()) for p in sorted(args.supplied_results.glob("*.json"))
]
assert len(field) == 243 and len({(r["dataset"], r["id"]) for r in field}) == 243
assert len(supplied) == 56 and len({(r["group"], r["file"]) for r in supplied}) == 56
summary = {
    "thresholds": {
        "max_low_band_fraction_exclusive": 0.0005,
        "min_centroid_range_hz": 700,
        "max_width_ratio": 0.8,
    },
    "field": {
        "recordings": len(field),
        "datasets": dict(Counter(r["dataset"] for r in field)),
        "changed_intervals": sum(r["baseline"] != r["candidate"] for r in field),
        "flagged_before": sum(bool(r["baseline"]) for r in field),
        "flagged_after": sum(bool(r["candidate"]) for r in field),
        "different_from_old_cache": sum(
            r["baseline"] != r["cached_baseline"] for r in field
        ),
    },
    "groups": {},
    "supplied": [],
    "field_intervals": [],
}
for group in sorted({r["group"] for r in supplied}):
    rows = [r for r in supplied if r["group"] == group]
    base = [
        v for r in rows for v in r["variants"] if v["gain"] == 1 and v["padding"] == 0
    ]
    variants = [v for r in rows for v in r["variants"]]
    summary["groups"][group] = dict(
        clips=len(rows),
        before=sum(bool(v["before"]) for v in base),
        after=sum(bool(v["after"]) for v in base),
        variants=len(variants),
        variants_before=sum(bool(v["before"]) for v in variants),
        variants_after=sum(bool(v["after"]) for v in variants),
        changed_variant_intervals=sum(v["before"] != v["after"] for v in variants),
    )
for row in supplied:
    summary["supplied"].append(
        {k: row[k] for k in ("file", "group", "sha256", "pcm_sha256", "variants")}
    )
for row in field:
    summary["field_intervals"].append(
        {k: row[k] for k in ("id", "dataset", "pcm_sha256", "baseline", "candidate")}
    )
summary["fresh_stream_runs"] = 2 * (
    len(field) + sum(len(r["variants"]) for r in supplied)
)
summary["implementation_sha256"] = {
    str(p): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in [
        Path("src/nfc_tools/analyzers/wingbeat_accompaniment.py"),
        Path("src/nfc_tools/analyzers/wingbeats.py"),
    ]
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(summary, indent=2) + "\n")
print(
    json.dumps(
        {
            k: v
            for k, v in summary.items()
            if k not in ("supplied", "field_intervals", "implementation_sha256")
        },
        indent=2,
    )
)
