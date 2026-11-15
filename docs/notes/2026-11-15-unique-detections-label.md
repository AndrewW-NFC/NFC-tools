# Unique detections label

Recorded November 15, 2026. Deferred under the project hold until January 10,
2027.

Requested change: rename `Independent detections` to `Unique detections`.

When implementing, update the species-comment label outside the NFC period in
`src/nfc_tools/ebird_export.py`, including numeric and pending-review comments,
and the expectations in `tests/test_ebird_export.py`. This is a wording change;
the counting and deduplication behavior should stay the same.

Reviewed `README.md`, `README_DEV.md`, and `README_WINGBEATS.md`. Keep their
current wording while the change is deferred. At implementation, update the
comment examples in the first two guides and the independent-detection totals
terminology in the wingbeat guide.
