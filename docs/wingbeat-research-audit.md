# WING instrumentation audit (2026-09-24)

Production baseline: `cd3f61ed3ea5b54f7b07f543feac24621e7fc316`.
The production WING source files are untouched. This phase does not tune gates, reorder routes, change production output, or train a classifier. The supplied archive remains unchanged; its extracted contents are under `research/wingbeat_research_codex_bundle/`.

## Integration

`tools/wingbeat_research_scan.py` is a research-only sidecar. Run it with the repository's installed Python environment (`.venv/bin/python`). It calls production `screen_window(samples, 24000)` for every window. Additional values cannot affect that result. It calls production `window_features`, `accompaniment_features`, `screen_accompaniment`, and `_smooth` for measurements. Route labels mirror the production broadband-first gates at 24 kHz; regression fixtures include an accompaniment-only signal with negligible energy below 3 kHz, not merely a signal passing both routes.

The scanner supports 24 kHz decoded input only. Legacy production 8 kHz behavior remains covered by existing tests, but this scanner is not an 8 kHz API. Source audio is opened read-only. Only FSD development data is selected. The absence of an Animal label is an operational negative selection rule, not independent proof that birds are absent.

## Audit findings and disposition

| Area | Finding | Action |
| --- | --- | --- |
| Imports | Supplied imports match the current checkout; local `_smooth` shadows an identical imported helper. Optional Numba copies the accompaniment implementation. | Remove shadowing and copied accelerator. Call production helpers directly. No Numba dependency or equivalence assumption remains. |
| Decision authority | Supplied `instrument_window` correctly calls production screening first. | Retain this authority and test input immutability. |
| Window/hop | Supplied slicer stops at an exactly full EOF window. Production reads again, advances one hop and evaluates the one-second overlapping tail. | Mirror production at lengths 0, below/at one second, below/at/above two seconds, exact multiples, and fractional tails. |
| Merging | Merge ordering and max score match production, but rounded endpoints and a 0.5 ms tolerance conceal small mismatches. | Store full precision and demand exact finite candidate tuple equality. CSV float round-trips preserve the score. |
| Decode | Bare `ffmpeg` fails where only the bundled decoder is installed. | Use `ensure_ffmpeg()` and the plugin's identical first-audio-stream, mono, 24 kHz float32 command flags. Preserve decoder errors and truncated-byte checks. |
| Broadband math | Frame size, hop, Hann window, band masks, raw/detrended envelopes, lag search, uncentered normalized dot products and band tests match production. | Retain these research detail calculations; verify coherent-band count and pulse selection against production. Do not substitute mean-centered accompaniment correlation for broadband correlation. |
| Pulse timestamps | Valid three-frame smoothing shifts index zero to the second original frame; supplied times omit its 10 ms offset. | Correct center to `peak*10 ms + 10 ms + 16 ms`. Times are relative to window start and remain coarse envelope centers, not annotated physical stroke times. |
| Pulse count | Peak region collapse, amplitude ordering and 0.6-period exclusion reproduce `distinct_pulses`. | Record research pulse count explicitly and test equivalence. It is zero if no period is found; production's fallback threshold-crossing count can differ in those no-period windows. |
| Width/attack/decay | Boundary pulses can be truncated. “Attack/decay” are half-height-to-peak distances, not full onset/offset durations. | Exclude boundary-censored widths. Retain documented 10 ms resolution; overlapping width regions may occur. Add above-threshold envelope duty fraction. |
| Rhythm | IPI SD uses sample SD; nPVI is mean `200*abs(diff(IPI))/(adjacent IPI sum)`. | Retain; SD/CV with only one interval are conventionally zero, not evidence of regularity. Missing nPVI for fewer than two intervals. |
| Kurtosis | Supplied value uses uncentered moments and an epsilon that distorts quiet signals. | Use central fourth/second moments, no additive epsilon in a nonzero denominator; silence is missing. Pearson kurtosis, not excess kurtosis. |
| Biphasic interpretation | Positive/negative extrema over 100 ms cannot demonstrate a biphasic aerodynamic impulse. Same-sign segments can produce negative “balance”. | Rename to `pulse_polarity_extrema_balance_median`, clamp absent polarities to zero; rename local peak-to-peak accordingly. This is only a sign-independent extrema balance, not stroke-shape evidence. |
| Synchrony | All-zero correlation ties produce arbitrary -50 ms “best” lags. | Require nonzero envelope norms; missing lag otherwise. Nonzero ties retain first-maximum behavior. |
| Spectral summaries | Centroid/entropy/rolloff summarize the mean spectrum of loud frames, not medians of individual-frame statistics; flux uses all frames. Silence rolloff was misleading. | Document exact aggregation; undefined spectral shape is missing on silence. |
| Comb | Strong short-spacing log-spectrum autocorrelation can arise from a smooth spectrum, not harmonics. Actual grid is 31.25 Hz; minimum tested spacing is 93.75 Hz. | Retain as exploratory spectral autocorrelation only; do not interpret as validated harmonicity or an insect fundamental. |
| Accompaniment | Best-band failed-gate summary hides failures in other bands. Bands without a valid local periodicity maximum are omitted by production. | Add per-search-band failed gates and measurement state. Missing means no selected period/invalid window, never a zero-valued measured feature. |
| Resumption | Counting partial chunks as 200 rows can skip windows; schemas vary for invalid windows. Final CSV could appear before validation completed. | Check contiguous full checkpoints; recompute partial tail; union CSV schemas; stage assembly and publish only after validation. Tests simulate an interrupted validation and partial checkpoint. |
| Provenance | Existing outputs could be reused after code/input changes; validation mismatches only warned. | Fingerprint scanner and production source, Python/NumPy, decoder version, input names/sizes/mtimes and metadata. Reject incompatible resume. Abort on mismatch, save errors, require complete counts before analysis. |

## Measurement limitations

Temporal measurements describe the **broadband envelope**, even when the accepted route is accompaniment. Accompaniment diagnostics are kept for each search band, but no new accompaniment pulse timestamp estimator is claimed. Noise, tones and weak sidelobes can yield research lag maxima in rejected windows. Analyze temporal features by route and ensure sufficient pulses. Envelope widths are smoothed acoustic measurements, not biomechanical wingstroke durations. No waveform pressure calibration or codec correction is applied.

The bundled xeno-canto tables have blank reference-validation fields throughout. They also used the older timing/morphology definitions. They are retained as historical input, not silently pooled with corrected data. The available 958 sources are re-instrumented into a separate T7 directory using this same scanner and sampled reference validation.

WAV header provenance uses Python's `wave` reader where supported; unsupported headers are flagged and decoding still uses FFmpeg. File extension describes the source container and is not proof of its codec. MP3 source sample rates, devices, microphones and uploader context can be joined from the original XC metadata in analysis; unknown values remain unknown. Fingerprints use input size/mtime (not whole-audio content hashes), so they detect ordinary changes but are not a forensic content-integrity guarantee. Full decoded recordings occupy memory in each worker; production streaming remains untouched.

## Validation and run commands

```sh
.venv/bin/python -m pytest tests/test_wingbeats.py tests/test_wingbeat_accompaniment.py tests/test_wingbeat_research.py -q
.venv/bin/python tools/wingbeat_research_scan.py fsd-hard-negatives \
  --audio-dir /Volumes/T7/FSD50K/FSD50K.dev_audio \
  --scan-csv research/wingbeat_research_codex_bundle/data/fsd50k_wing_scan_dev.csv \
  --out /Volumes/T7/FSD50K/wing_research_hard_negatives \
  --workers 4 --validate-reference
.venv/bin/python tools/wingbeat_research_scan.py xc \
  --audio-dir /Volumes/T7/xc-wingbeats/audio \
  --metadata /Volumes/T7/xc-wingbeats/metadata.csv \
  --out /Volumes/T7/xc-wingbeats/research_v2 \
  --workers 4 --validate-reference
```

With validation enabled, the first five files and each subsequent zero-based index divisible by 100 (filename order) are checked against production `detect_stream()` using exactly the same decoded float32 bytes. This deterministic sample is not a random sensitivity estimate. Every window's score is still obtained directly from production, whether its file is selected for full-stream validation or not.

Tests: **290 passed** (233 existing WING tests plus 57 research regressions), 11.59 s in the repository environment. Tests include real stereo-WAV decoding, invalid/NaN inputs, separate/touching merges, sub-sample endpoint preservation, exact score equality, both production routes, short/exact/fractional EOF, pulse helper equivalence, schema union, fail-closed validation, and checkpoint interruption.

Initial incomplete runs were stopped after finding the publication-order issue. Their newly generated outputs were preserved under `wing_research_hard_negatives_initial_incomplete` and `research_v2_initial_incomplete` on T7. Final runs use fresh canonical output directories and consistent provenance. These initial outputs are excluded from analysis.

## Analysis outputs and interpretation

`tools/analyze_wingbeat_research.py` requires complete scan summaries with nonzero reference checks and zero errors/mismatches. It checks duplicate windows and aggregates **accepted windows only** to one median per recording for feature comparisons. These are recording-balanced descriptions of current candidate populations, not event-localized class labels. It records P10/P25/median/P75/P90, Cliff's delta with tie handling, histogram overlap using pooled quantile bins, and the fraction of XC values inside FSD's P10–P90 interval. Exact Cliff's-delta calculations were independently checked against all pairwise signs on tied, identical and separated small samples.

Contrasts include broadband only, accompaniment only, WAV only, short (≤15 s) exact wingbeats-only metadata, and uploader medians. Subtype comparisons use non-exclusive FSD recording labels for footsteps/running, applause/clapping, clocks/ticking, machinery/vehicles/tools, and rain/wind. They do not localize which labeled sound caused a detection. No model is trained and no thresholds are optimized. Dataset selection already conditions on WING acceptance, so gate pass fractions cannot justify gate removal or estimate specificity on the full development set.

Original XC metadata supplies declared source rate, uploader, device and microphone information in `file_provenance.csv`; FSD uploader names come from `FSD50K.metadata/dev_clips_info_FSD50K.json`. Missing provenance stays missing. Source extension is only a format proxy. WAV-only and uploader summaries are sensitivity checks, not a cure for dataset/species/recording-context confounding.

`tools/plot_wingbeat_research.py` produces a standalone PNG of recording-level ECDFs. Horizontal axes show pooled 1st–99th percentiles for readability; all observations remain in the numerical summaries and the full ECDF CSV.

Analysis example (Python environment with pandas and NumPy):

```sh
python tools/analyze_wingbeat_research.py \
  --fsd /Volumes/T7/FSD50K/wing_research_hard_negatives \
  --xc /Volumes/T7/xc-wingbeats/research_v2 \
  --xc-metadata /Volumes/T7/xc-wingbeats/metadata.csv \
  --fsd-metadata /Volumes/T7/FSD50K/FSD50K.metadata/dev_clips_info_FSD50K.json \
  --bundle-data research/wingbeat_research_codex_bundle/data \
  --out /Volumes/T7/FSD50K/wing_research_comparison_2026-09-24
python tools/plot_wingbeat_research.py /Volumes/T7/FSD50K/wing_research_comparison_2026-09-24
```

Plotting additionally requires Matplotlib. These are optional research dependencies; production package dependencies are unchanged.

The analysis reconstructs all merged event intervals in `candidate_events.csv` and checks every selected FSD file against the first-pass candidate list at that CSV's three-decimal precision. The production-stream comparisons performed by the scanner remain exact, with no tolerance. `xc_historical_window_audit.csv` distinguishes omitted EOF windows from score/route/decision disagreements on shared windows.
