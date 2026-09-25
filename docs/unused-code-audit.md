# Unused-code review — 2026-09-25

## Scope and method

Reviewed the production Python package, browser JavaScript, templates and styles,
CLI/GUI entry points, analyzer registration, developer scripts, and research tools.
Used Ruff/Pyflakes, Vulture, Python AST and repository-wide reference searches,
ESLint's unused-variable check, and a full test run with coverage. Each removal
was checked against callers and string-based template/browser references; missing
test coverage alone was not treated as proof of unused code.

## Removed

- `_unique_clip_path`: superseded by stable occurrence-based clip naming in
  `export_analyzer_clips`; retries must overwrite the same completed clip.
- `geocode.lookup`: the old location-name search had no callers. Coordinate-based
  timezone lookup remains in use by Settings and Import Recordings.
- `scheduler.next_relevant_window`: superseded by
  `schedule_resolver.next_window_for_config`. Moved its after-end/naive-datetime
  regression coverage to that active resolver; kept shared window primitives.
- `analyzers.all_names` and its unused re-export.
- `Notifications.on_failure`: never read or exposed in the UI. Existing YAML
  containing this field remains loadable through Pydantic's default extra-field
  handling. The active session-end notification option remains.
- Dashboard `sameLocalDate` and write-only `meterPreviewRequiresDemand` state.
- Four unused Python imports and one unused research result binding. The
  `Future.result()` call remains so worker failures still propagate.
- Styles for twelve retired class names, including the old brand/container,
  diagnostics grid, timing-mode controls, and optional-field layout.

## Kept deliberately

Framework-dispatched FastAPI routes, Click commands, Pydantic validators,
PortAudio/context-manager callback signatures, analyzer self-registration imports,
and serialized measurement fields are active despite static-tool warnings.
Dynamically generated `status-*` and `estimate-*` CSS classes remain. Legacy
recording filenames and import-request compatibility paths are still supported.
The original research bundle and archive are preserved as provenance; the audited
scanner in `tools/` remains the operational version. Production WING detection
logic and thresholds were not changed by this cleanup.

## Validation

- 539 Python tests passed, including WING detector/research and import/live parity.
- 31 browser timeline tests passed; all seven browser scripts passed syntax checks.
- Ruff's complete `F` rule group and JavaScript unused-variable checks passed.
- Full-suite Python statement coverage was 67%; production WING was 98%.
  Hardware, OS integrations, and CLI paths need separate checks, so this is not
  a claim of complete runtime coverage.
- CI now runs the Python reference/unused-code checks and discovers all browser
  scripts for syntax checks instead of maintaining an incomplete filename list.
