# Reported WING false negative — November 10, 2026

Status: targeted recovery implemented. The current detector flags 7.75–8.75 s
of the supplied recording. Species remains unconfirmed.

The user reports that `amewoo (0.601)-BirdNET_01.wav` should register as
WING, is not a woodcock, and is probably a duck. Preserve that as a user
annotation, not a verified species identification. The filename is not ground
truth. WING is a review candidate, not a species label.

Before the fix, the 11.008-second clip produced zero candidates through
`detect_stream` at the production 24 kHz analysis rate. `measurements.json`
preserves that baseline and records the source path,
SHA-256, code revision, and all 121 scheduled windows with their measured
features. The original desktop attachment was no longer present during follow-up.
The November 9 source clip was located at the path in
`../../../tests/fixtures/reported-wing-miss-provenance.json`. Its container hash
differs, but all broadband and accompaniment features in all 121 baseline
windows match exactly. A three-second PCM16 crop (original 7–10 s) is retained
as `../../../tests/fixtures/reported-wing-miss.wav` for regression testing.

## Rejection evidence

The 3,500–6,500 Hz search band tracks pulse-associated energy near 4.7–4.8 kHz
late in the clip. Representative windows show several independent failures:

- **7.50–9.50 s:** periodicity 0.560 and second-repeat correlation 0.325 fail
  the normal 0.60/0.35 rhythm requirements. The near-miss route also fails its
  0.40 second-repeat and 0.70 noise-coherence requirements (coherence 0.687).
  Pulse-excess flatness is 0.411, but low-band fraction 0.000499 and ridge
  prominence 5.413 fail the bass-or-prominent-ridge support requirement
  (0.005 or 16). Localized-pulse support also fails its stronger rhythm and
  noise-coherence requirements.
- **7.75–9.25 s:** periodicity 0.571 fails the standard rhythm requirement.
  Even allowing the near-miss rhythm on this shorter window would not suffice:
  pulse-excess flatness is 0.037, low-band fraction 0.000461, and ridge
  prominence 5.413. Four counted pulses also fall below the localized route's
  six-pulse requirement.
- **8.00–9.00 s:** the strongest periodicity in this search band is 0.580,
  with second-repeat correlation only 0.220.

This reproduces a screening miss directly, before review/export handling. It
does not establish the species, the original full-recording context, or a
single implementation error. The supplied clip fails multiple intentional
screening gates; simply relaxing one cutoff does not resolve it.

## Recovery and validation

The narrow moving maximum is a poor rhythm measurement for this broad,
noise-like pulse train: fine spectral texture changes which bins dominate.
The two upper search bands now also measure a fixed region extending 750 Hz
either side of the median spectral maximum. The original measurements remain.
This additional measurement can only use the existing localized-lobe route;
it cannot use the more permissive spectral-support route. No acceptance
thresholds were lowered. The call-motion and upper-interference vetoes remain.

At 7.75–8.75 s, the fixed measurement has periodicity 0.629, second-repeat
correlation 0.846, noise coherence 0.818, six pulses, and effective lobe width
about 705 Hz. These pass the existing localized-pulse requirements.

- The three-second regression crop passes all 18 combinations of gains
  0.1/1/3 and leading silence 0/.07/.19/.25/.5/.75 s. These are robustness
  checks on one example, not independent biological positives.
- Cached and uncached results match. Diagnostic output now distinguishes
  ridge and fixed-lobe measurements instead of overwriting one with the other.
- Full test suite: 1,156 passed, 3 skipped (`.venv/bin/pytest -q`).
- `compare_synthetic.py` reproduces `synthetic-comparison.json`: 12 signal
  families, ten deterministic seeds each, with identical before/after
  detection intervals. This includes one existing click false positive.
- `timing.json` records three runs each on the 11.008-second source: median
  processing time rose from 0.654 s to 0.847 s (about 30%). This is a short-clip
  measurement on this machine, not a full-night throughput benchmark.

The broader field-control archive is on an unmounted external drive and was
not rerun. Existing measured waterfowl/robin fixtures and synthetic regression
tests provide narrower coverage; unchanged synthetic results do not establish
unchanged field false-positive rates. This fixes the reported screening miss
but does not identify the bird or establish complete passage coverage.

## Second user-reported miss: purfin filename

`purfin (0.92)-BirdNET_01.wav` (11.008 s) was supplied after the fixed-lobe
change. Without the fixed-lobe features it produces no candidates. The existing
updated detector flags **6.75–8.25 s**, through the 3,500–6,500 Hz fixed-lobe
measurement. No further production change was needed for this supplied clip.
`purfin-validation.json` preserves source hashes, before/after intervals and
accepted-window features. The filename is not a verified species label.

A PCM16 crop of original seconds 6–9 is included as a second regression fixture.
At its original alignment it passes at gains 0.1, 1 and 3, and the baseline
ridge-only features reject its accepted window. It passes 12/18 crop gain/timing
variants, but **fails all six variants with 0.07 or 0.19 s leading silence**.
Those six desired-behavior tests are retained as strict expected failures;
they run normally and will report an unexpected pass when the limitation is
resolved. The first clip still passes all 18 variants.

The full second recording was also checked at unity gain with those offsets:
0.07 s produces a later candidate at 9.25–10.25 s, while 0.19 s produces no
candidate. Thus recovery of the supplied file does not establish reliable
recovery at arbitrary positions within a full-night recording. This alignment
limitation remains unresolved; no threshold relaxation was made to conceal it.
