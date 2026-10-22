# Wingbeat frame reuse — October 22, 2026

The streaming analyzer now shares frame-local FFT spectra, local spectral medians,
and frequency masks across overlapping windows. Window-dependent statistics,
smoothing, gates, pass scheduling, scores, and interval merging remain unchanged.
Each stream owns its caches, bounded by the current two-second region.

## Local benchmark

Three runs per mode on the same decoded 24 kHz mono PCM, alternating mode order.
Times below are medians for screening only; decoding and output writing are excluded.
Inputs are the existing Macaulay waterfowl review previews on T7, capped at 35 seconds.
The first sample overlapped the tail of the test run, so these are indicative local
measurements, not controlled full-night throughput estimates.

| Recording | Audio seconds | Uncached seconds | Cached seconds | Speedup | Detections |
|---|---:|---:|---:|---:|---:|
| ml-645008811.wav | 32.58 | 7.55 | 1.73 | 4.37× | 2 |
| ml-475055411.wav | 17.30 | 3.73 | 0.86 | 4.33× | 1 |
| ml-211014411.wav | 35.00 | 7.78 | 1.82 | 4.26× | 2 |

Every run produced exactly equal candidate intervals and scores. No source audio
or analysis output was modified. This measures runtime, not new accuracy evidence.

Reproduce with `scripts/benchmark_wingbeats.py --seconds 35 --repeats 3 <recordings...>`
using the project virtual environment. The uncached mode retains the original
per-window computation for comparison.

## Verification

- 990 Python tests passed; 3 platform skips.
- 41 browser JavaScript tests passed.
- Exact per-window feature equality on noise, broadband pulses, pulsed tonal
  accompaniment and silence; stream equality with short reads, NaNs and tails.
- Bounded-cache and frame-reuse checks passed.
- Python reference/import checks, compilation, JavaScript syntax, version and
  dependency consistency, and diff whitespace checks passed.
- Wheel built successfully and includes the cache module and updated log wording.
