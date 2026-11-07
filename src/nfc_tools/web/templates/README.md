# Recorder page templates

Jinja2 templates render the main recorder UI. `base.html` supplies navigation, shared styling, and the common controller. Full pages extend it; `ebird_location.html` and `ebird_rarity.html` are reusable form fragments.

Route modules in the parent folder provide template variables and form endpoints. [Browser scripts](../static/README.md) depend on the element IDs, classes, and data attributes here; update both sides when changing those contracts. File headers name each page's route and script dependencies.
