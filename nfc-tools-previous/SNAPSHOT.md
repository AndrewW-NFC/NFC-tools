# NFC Tools 0.8.2 — pre-BirdNET-3 source snapshot

This folder preserves the tracked source files from commit
`c270c57` (Use readable names for non-avian BirdNET clip exports), the working
version immediately before the BirdNET 3 merge. Its declared app version is
0.8.2 and it uses BirdNET Analyzer/model 2.4.

This is the pre-upgrade working snapshot, not the exact October 24 `v0.8.2`
release tag: it also includes subsequent fixes that were already on main.
Except for this explanatory file, its contents match that commit. It has no
nested Git repository, virtual environment, downloaded models, or personal settings.

The parent repository is NFC Tools 0.8.3. Keep this snapshot unchanged; make new
improvements in the parent's source tree. The parent test suite and distribution
build do not include this archived application. To test this version itself,
run its commands from this directory.

## Run this version separately

Close any running NFC Tools app first. From the repository root on macOS/Linux:

```bash
cd nfc-tools-previous
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/nfc-tools
```

On Windows PowerShell:

```powershell
cd nfc-tools-previous
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\nfc-tools.exe
```

Both versions use the normal NFC Tools settings and port, so run only one at a
time. Version 0.8.2 uses `analyzers/birdnet`; 0.8.3 uses `analyzers/birdnet3`.
Install BirdNET through Settings if the older analyzer is not already present.
Use separate output folders: this old app cannot detect mixed BirdNET versions.
To return to 0.8.3, close this app and run the parent installation's launcher.
