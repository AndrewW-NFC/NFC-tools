# BirdNET → eBird name crosswalk

NFC Tools bundles a versioned crosswalk so BirdNET names such as **Eastern Screech Owl** become eBird's **Eastern Screech-Owl** in upload files. It runs offline when exports are generated. Raw analyzer results and clip names are preserved.

## Reviewing exports

The review CSV includes these columns even when eBird uploads are disabled:

| Column | Meaning |
| --- | --- |
| `common_name`, `scientific_name` | Canonical eBird names for mapped detections; original names for excluded detections. |
| `original_common_name`, `original_scientific_name` | Original BirdNET CSV names. |
| `taxonomy_status` | `mapped` is eligible for upload; `review_required` needs taxonomic review; `non_bird` is excluded. Other analyzers retain their existing status rules. |
| `taxonomy_reason` | Crosswalk evidence classification, or `unknown_scientific_name` for an unrecognized/missing scientific name. |
| `taxonomy_version` | Exact crosswalk release used for BirdNET rows. |
| `candidate_common_name`, `candidate_scientific_name`, `candidate_species_code` | Possible eBird match for review only, never automatically uploaded. Blank when no candidate exists or the mapping is accepted. |

Uncertain rows remain in both the session and nightly review CSVs but are excluded from upload CSVs. The command-line summary and application session log report the number of BirdNET review rows needing taxonomy review. Counts are aggregated review rows, not individual detections. Non-bird detections are also retained for review and excluded from eBird uploads.

Check uncertain identifications and their current taxonomic scope before manually adding the appropriate eBird taxon to your checklist. Editing a review CSV does not update the crosswalk or upload CSV; regenerating exports replaces those files. Existing exported files change only when regenerated.

## Release birdnet3-ebird2026-r1

- Model: installed BirdNET 3.0 preview 3.1 acoustic English (`en_us`) labels, with shared taxonomy v0.2-Jun2026.
- Target: eBird v2026 English taxonomy, retrieved 2026-11-08 from the [eBird taxonomy API](https://api.ebird.org/v2/ref/taxonomy/ebird?fmt=csv&locale=en). The [versions endpoint](https://api.ebird.org/v2/ref/taxonomy/versions) identified 2026 as latest.
- [Crosswalk CSV](../../src/nfc_tools/data/birdnet_ebird_crosswalk_v2026_1.csv): one searchable row per BirdNET scientific name, including source names, target names/code/category, status, and reason.
- [Manifest](../../src/nfc_tools/data/birdnet_ebird_crosswalk_v2026_1.json): release identifier, input hashes, output SHA-256, policy, and status totals.
- [Audit report](../evaluations/birdnet-ebird-taxonomy-2026-11-08/README.md) and [machine-readable audit](../evaluations/birdnet-ebird-taxonomy-2026-11-08/audit.json): full comparison evidence.

The initial release maps 9,561 bird labels (including 1,474 differing common names), flags 273 bird labels, and excludes 1,726 non-bird labels.

## Matching policy

The initial accepted mappings require a unique **exact scientific-name match** in the eBird snapshot. Common names can differ in punctuation, capitalization, regional spelling, or naming convention. Runtime lookup uses the scientific name with leading/trailing whitespace stripped; it does not fuzzy-match, infer from common names, or trust analyzer species codes. Unknown or missing scientific names require review. This also handles older/localized common names when their scientific name is covered.

A cached species-code match or common-name-only match is a candidate, not approval. Changed genera, splits, lumps, and subspecies require review. Scientific-name equality is evidence for name reconciliation, not proof that historical taxonomic scope is identical. A future known scope conflict must be marked `review_required`, even if the scientific name is unchanged.

Mapped names are used before aggregation and rarity annotation, so different source labels that resolve to the same taxon share an upload row. Review rows preserve distinct original names. Missing/corrupt bundled data fails the export instead of falling back to unverified names.

## Rebuilding and updating

Reproduce the initial CSV and manifest from the checked-in audit:

```sh
python scripts/build_birdnet_ebird_crosswalk.py \
  docs/evaluations/birdnet-ebird-taxonomy-2026-11-08/audit.json \
  src/nfc_tools/data/birdnet_ebird_crosswalk_v2026_1.csv \
  --version birdnet3-ebird2026-r1
```

For a new release:

1. Save a fresh comparison of the intended model labels against a dated eBird taxonomy snapshot. Record input SHA-256 hashes and URLs. Follow the audit schema: one row per model scientific name, original names, evidence `status`, and candidate eBird names/code/category when available. Separate non-birds; do not turn ambiguous/common-name-only matches into exact matches.
2. Review changes, especially splits/lumps, previously accepted mappings that disappear, and candidate matches. The builder only accepts `exact`, `capitalization`, `punctuation_spacing`, and `other_common_name_change` evidence with equal scientific names and a target code/name. All other evidence stays review-only except `non_bird`.
3. Generate a **new** CSV/manifest filename and version (`r2`, or a new eBird year); preserve the prior release evidence in Git. Record any manually researched decisions and supporting source in the audit report. A synonym approval with unequal scientific names requires an explicit policy/code change and regression test, not relabeling it as an exact match.
4. Update `RESOURCE` in `src/nfc_tools/birdnet_taxonomy.py`, this document, and regression fixtures/count expectations. Check the CSV diff and manifest totals. Run taxonomy/export tests and package checks. Commit the audit, crosswalk, manifest, code, and documentation together.

No taxonomy download or automatic refresh occurs during normal use. The CSV is the easily inspected mapping table; the manifest pins its contents and the review CSV records which release was applied.
