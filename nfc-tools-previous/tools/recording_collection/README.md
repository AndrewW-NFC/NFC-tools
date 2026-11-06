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
