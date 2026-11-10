# Measured regression fixtures

Small JSON fixtures preserve measured features and provenance for wingbeat regressions without bundling the original audio.

- `waterfowl-window-features.json`: feature windows used by waterfowl recovery tests.
- `robin-motion-features.json`: measured motion/interference windows used by call-motion tests.
- `mute-swan-provenance.json`: provenance for the mute-swan regression material.
- `reported-wing-miss.wav` and `reported-wing-miss-provenance.json`: three-second
  crop and provenance for the November 10 user-reported WING false negative;
  species unconfirmed.
- `reported-wing-miss-purfin.wav` and its provenance JSON: three-second crop
  of the second November 10 user-reported miss, already recovered by the fixed
  lobe measurement at its original alignment. The filename is not a species ID.

Consumers live in the parent test folder. Treat these as evidence snapshots: changes should have a traceable source and retain the meaning of existing regression cases. The separate `../precipitation-fixtures.json` tests the rainfall contract.
