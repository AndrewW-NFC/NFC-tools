# Recording collection tools

These are the maintained source copies of the collection-management commands on
T7. From this repository, always pass `--root` (or set `WINGBEAT_DATA_ROOT` for
recordings.py and resolve_path.py). The installed T7 copies can infer their root
from `tools/collection-management/`; repository copies cannot infer the T7 mount.

```sh
python tools/recording_collection/recordings.py summary --root '/Volumes/T7/Wingbeats detector' --group waterfowl
python tools/recording_collection/recordings.py list --root '/Volumes/T7/Wingbeats detector' --id ml-211014411
python tools/recording_collection/resolve_path.py 'OLD_PATH' --root '/Volumes/T7/Wingbeats detector'
```

Extraction requires an explicit ID/group and destination, verifies the original
hash and size, and refuses overwrites. `audit_references.py` accepts explicit
`--root` and `--repo` paths and writes a reference-audit report; it does not rename
or repair files. Source recordings, manifests, migration tables and historical
snapshots stay on T7, not in Git.

## Files and dependencies

- `recordings.py`: lists/summarizes the recording catalog and extracts explicitly selected archive members after checking size and hash. Depends on `catalogs/recordings.csv` and the referenced archives.
- `resolve_path.py`: translates historical paths using `catalogs/path-migrations.csv`.
- `audit_references.py`: scans stored links and paths, using `resolve_path.py`, and writes an audit report.

All three use Python's standard library. Their catalogs and audio archives are external collection data, not bundled application resources.
