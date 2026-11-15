# Awaiting manual review text

Recorded November 15, 2026. Deferred under the project hold until January 10,
2027.

Requested change: remove this sentence from checklist comments:

> Call counts are automated estimates unless manually reviewed; detection windows may contain multiple calls.

Return to the existing `Awaiting manual review` text. Preserve other checklist
comment details and counting behavior.

The sentence is appended alongside `DEFAULT_CHECKLIST_COMMENT` in
`src/nfc_tools/ebird_export.py`. When implementing, remove that added sentence
and update the corresponding expectations in `tests/test_ebird_export.py`.

Reviewed `README.md`, `README_DEV.md`, and `README_WINGBEATS.md` for relevant
wording. At implementation, update the developer guide's statement that
checklist comments explicitly describe automated estimates. Retain the guides'
explanations of counting limitations; no behavior change is proposed. The
guides remain unchanged while this request is deferred.
