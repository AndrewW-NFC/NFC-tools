# Measured regression fixtures

Small JSON fixtures preserve measured features and provenance for wingbeat regressions without bundling the original audio.

- `waterfowl-window-features.json`: feature windows used by waterfowl recovery tests.
- `robin-motion-features.json`: measured motion/interference windows used by call-motion tests.
- `mute-swan-provenance.json`: provenance for the mute-swan regression material.

Consumers live in the parent test folder. Treat these as evidence snapshots: changes should have a traceable source and retain the meaning of existing regression cases. The separate `../precipitation-fixtures.json` tests the rainfall contract.
