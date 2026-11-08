"""Build a reviewable, versioned crosswalk from a saved taxonomy audit.

Role: Offline data maintenance; never fetches or changes taxonomy at runtime.
Dependencies: Python standard library; see docs/reference/birdnet-ebird-crosswalk.md.
"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ACCEPTED = {"exact", "capitalization", "punctuation_spacing", "other_common_name_change"}
FIELDS = ["birdnet_scientific", "birdnet_common", "status", "reason", "ebird_common",
          "ebird_scientific", "ebird_code", "ebird_category"]


def build(audit_path, output, version):
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    rows = []
    seen = set()
    for source in audit["rows"]:
        sci = source["birdnet_scientific"]
        if not sci or sci in seen:
            raise ValueError(f"Missing or duplicate scientific name: {sci}")
        seen.add(sci)
        reason = source["status"]
        status = "review_required"
        if reason in ACCEPTED:
            if (sci != source.get("ebird_scientific") or not source.get("ebird_code")
                    or not source.get("ebird_common")):
                raise ValueError(f"Invalid scientific-name match: {sci}")
            status = "mapped"
        elif reason == "non_bird":
            status = "non_bird"
        rows.append({**{key: source.get(key, "") for key in FIELDS},
                     "status": status, "reason": reason})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: row["birdnet_scientific"]))
    manifest = {"version": version, "file": output.name,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                "audit_sha256": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
                "source_sha256": audit["sources"], "ebird_url": audit["ebird_url"],
                "counts": dict(Counter(row["status"] for row in rows)),
                "policy": "Unique exact scientific-name matches only; other candidates require review."}
    output.with_suffix(".json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build(args.audit, args.output, args.version)
