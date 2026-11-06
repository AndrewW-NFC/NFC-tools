# Changes pending incorporation into nfc-tools-dev

## 2026-11-06 — Readable non-avian BirdNET clip filenames

Status: incorporated into the combined `codex/birdnet-3-integration` branch.
The standalone development checkout remains unchanged.

- Port the filename display-name selection and `BIRDNET_NON_AVIAN_CODES` from
  `src/nfc_tools/clip_exporter.py`, plus the regression coverage in
  `tests/test_clip_exporter.py`.
- Prefer the result's common name for `t-` taxon IDs and the non-avian sound
  codes dogdog, engine, envrnm, frwrks, gungun, humnov, humvoc, humwhi, powtoo,
  and siren1. Example: `Wood Frog (0.812)-BirdNET.wav`.
- Keep bird abbreviations, original identification codes in embedded metadata,
  and code fallback when the common name is absent. Continue excluding nocall.
- Applies to newly exported clips; existing files are not renamed. Re-exporting
  an older result can leave both its old code-based clip and its new named clip.
- Validate with `.venv/bin/python -m pytest tests/test_clip_exporter.py`.
- When incorporated, record the destination commit here and mark this complete.
