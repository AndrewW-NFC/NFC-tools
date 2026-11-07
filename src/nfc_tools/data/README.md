# Bundled application resources

Resources in this folder ship with the Python package. `ebird_export.py` reads `nighthawk_ebird_taxonomy.csv` to map Nighthawk labels to eBird taxonomy. `__init__.py` enables package-resource lookup. [sounds](sounds/README.md) contains the completion chime and its attribution.

CSV and audio contents are data contracts/assets rather than source files; their purpose is documented here instead of inserting comments into their formats.

## Files

| File | Purpose |
| --- | --- |
| [__init__.py](__init__.py) | Bundled taxonomy and notification sound resources. |
