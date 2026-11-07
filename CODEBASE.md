# Codebase guide

NFC Tools records nocturnal audio, runs analyzers, exports review material, and exposes a local browser interface. This guide and the README in each maintained code folder explain where to look. File headers state purpose, role, and important dependencies.

## Start here

| Folder | Contents |
| --- | --- |
| [src](src/README.md) | Installable application source. |
| [src/nfc_tools](src/nfc_tools/README.md) | Recording, scheduling, imports, exports, configuration, and shared helpers. |
| [analyzers](src/nfc_tools/analyzers/README.md) | BirdNET/Nighthawk adapters and experimental wingbeat screening. |
| [web](src/nfc_tools/web/README.md) | Recorder HTTP routes, page templates, and browser controllers. |
| [review](src/nfc_tools/review/README.md) | Separate workspace for human listening and annotations. |
| [data](src/nfc_tools/data/README.md) | Packaged taxonomy and completion audio. |
| [tests](tests/README.md) | Python and Node regression tests and measured fixtures. |
| [scripts](scripts/README.md) | Consistency checks, benchmarks, and focused evaluation commands. |
| [tools](tools/README.md) | Research scanning, reporting, collection, and review evaluation. |
| [docs](docs/README.md) | Integration notes, contracts, reference material, and dated evaluations. |
| [research](research/README.md) | Preserved research handoffs. |
| [.github](.github/README.md) | CI workflow configuration. |
| `nfc-tools-previous` | Historical source copy; excluded from current source distributions. |

Generated folders such as `.venv`, `dist`, `__pycache__`, and test/lint caches are not maintained source. Historical source copies and evaluation snapshots retain their original contents.

## Follow a feature

- **Record audio:** `app.py` / `cli.py` → `web/routes.py` or `session.py` → `recorder.py` / `sounddevice_recorder.py` → `analyzers`.
- **Import recordings:** import template/controller → `web/routes_import.py` → `importer.py` → shared analysis and export helpers.
- **Inspect or recover a night:** `web/routes_nights.py` → `night_status.py` and `session.py`; manifests and checkpoints preserve progress.
- **Export detections:** analyzer outputs → `clip_exporter.py` and `ebird_export.py`; `clip_metadata.py` preserves source provenance.
- **Review by listening:** `review/__main__.py` → batch preparation or the review server → its independent browser assets and annotation database.

## Root files

- `README.md`: user introduction and setup.
- `README_DEV.md`: developer setup and validation commands.
- `README_WINGBEATS.md`: detector behavior, limitations, and recording credits.
- `pyproject.toml`: Python package metadata, dependencies, entry points, and tool configuration.
- `briefcase.toml`: desktop packaging configuration and dependency declarations.
- `VERSION` and `src/nfc_tools/version.py`: release declarations checked alongside packaging metadata by `scripts/check_versions.py`.
- `CHANGELOG.md`: release history; `LICENSE`: project license. Asset-specific licenses remain beside their assets.
- `.gitignore` and `.gitattributes`: tracked-file exclusions and Git file handling.

## Keeping these explanations useful

Python files retain their module docstring for purpose, followed by `Role` and `Dependencies` comments. Browser assets use a leading comment; Jinja templates use template comments so documentation is not rendered. Folder READMEs describe direct contents and link to child guides.

Describe key collaborators, external tools/services, and data contracts rather than copying every standard-library import. Distinguish optional/platform dependencies from universal ones. Update the nearby header and folder guide when responsibilities move. JSON/CSV/audio assets are explained by their folder guides instead of adding invalid comments to their contents. Dependency versions remain authoritative in the packaging manifests.
