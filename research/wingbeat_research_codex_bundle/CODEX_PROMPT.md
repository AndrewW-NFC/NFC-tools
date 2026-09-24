# Prompt for Desktop Codex

You are working inside my existing `nfc-tools` repository. I have placed `wingbeat_research_codex_bundle.zip` in the repository folder. This archive contains research instrumentation and data from an ongoing effort to improve the experimental WING wingbeat detector.

Please take ownership of the next engineering/research step, but be conservative with the production detector.

## First: inspect, do not immediately rewrite

1. Inspect the current repository and current git status.
2. Inspect the existing WING implementation, especially the broadband and tonal/accompaniment routes and their tests.
3. Unpack/read the bundle and read `STATE_OF_WORK.md`, `FEATURE_DICTIONARY.md`, and `tools/wingbeat_research_scan.py`.
4. Audit the research scanner against the *current checkout* of NFC Tools. Do not assume the scanner is correct merely because it was previously run successfully. In particular, check all imports, feature calculations, window/hop behavior, candidate merging, audio decoding, route labeling, and any reimplemented helper math for numerical equivalence to current production behavior where equivalence is claimed.
5. Tell me briefly what you found before making any substantial architectural changes. You may fix obvious integration/runtime issues as needed, but do not change production WING thresholds or detection logic.

## Core requirement: production decisions must not change

The purpose of this phase is to **instrument WING, not improve WING yet**.

Treat the existing repository's production `screen_window()` / `detect_stream()` behavior as authoritative. The research instrumentation may calculate and save additional values, but no new measurement may feed back into a production accept/reject decision.

Do not change:

- WING thresholds
- broadband gate logic
- accompaniment gate logic
- route ordering
- window/hop behavior
- candidate merge behavior
- existing output semantics

If you need to refactor production code to expose measurements, first prove with tests that detections are identical before and after. Prefer a research-only module/script if that avoids touching production code.

Add regression tests that demonstrate that instrumentation does not change WING decisions. Test both broadband and accompaniment cases and, if practical, compare complete candidate lists from `detect_stream()` against reconstructed candidates from the research scanner.

## Data already available in the bundle

`data/fsd50k_wing_scan_dev.csv` is the completed first-pass scan of the full FSD50K development set:

- 40,966 files analyzed
- 3,923 files triggered current WING
- 4,897 candidate intervals
- 3,343 of the triggering files have no `Animal` label; these are the environmental hard-negative candidates we want to instrument next

The actual FSD50K development WAVs are on my external drive here:

`/Volumes/T7/FSD50K/FSD50K.dev_audio`

Do **not** use the FSD50K evaluation set yet.

The xeno-canto wingbeat corpus has already had the research scanner run over it. The bundle contains:

- `data/xc_wingbeat_research_files.csv`
- `data/xc_wingbeat_research_windows.csv.gz`

Those represent:

- 958 recordings known at the recording level to contain wingbeats
- 44,280 two-second windows
- 3,996 windows accepted by current WING
- 1,522 merged WING candidate events
- 467 recordings with at least one current-WING candidate

Important: these are **weak positive labels**. Many source recordings include calls/song plus wingbeats, so do not label every xeno-canto window as a true wingbeat. Do not report the 467/958 figure as detector sensitivity.

## Instrumentation goals

The research dataset should preserve the exact current WING result for every analysis window while recording continuous measurements that can later tell us why real wingbeats differ from confounders.

Audit and retain, where sound, measurements including:

- current WING score, route, pass/fail state, and individual failed gates
- existing broadband feature values
- estimated beat rate / period
- pulse times and pulse count
- inter-pulse-interval mean, SD, CV, and a rhythm-variability measure such as nPVI
- pulse width, attack, decay, duty-cycle/morphology summaries
- cycle-to-cycle amplitude variation
- waveform RMS, crest factor, kurtosis/impulsiveness, zero-crossing rate
- sign-independent biphasic/pulse-shape information
- spectral centroid, bandwidth, rolloff, entropy, crest, flux
- harmonic/comb diagnostics useful for insect or machinery confounds
- each existing pulse band's modulation/coherence/synchrony values rather than only a count of coherent bands
- tonal/accompaniment features for each existing search band
- provenance fields sufficient to distinguish xeno-canto recordings, FSD50K recordings, codec/source format, and labels

If a proposed measurement is unreliable or incorrectly implemented in the supplied scanner, fix or remove it and document why. Do not preserve a feature just because it is listed here.

## Run the FSD50K hard-negative instrumentation

After the scanner passes your audit/tests, run it against only the 3,343 FSD50K non-Animal files that triggered WING in the first pass. Keep outputs on the T7.

The intended command shape is approximately:

```bash
python wingbeat_research_scan.py fsd-hard-negatives \
  --audio-dir "/Volumes/T7/FSD50K/FSD50K.dev_audio" \
  --scan-csv "<path to bundle>/data/fsd50k_wing_scan_dev.csv" \
  --out "/Volumes/T7/FSD50K/wing_research_hard_negatives" \
  --workers 4 \
  --validate-reference
```

Adapt paths/module placement to the repository structure you choose. The run should be resumable/checkpointed and must not modify the source WAVs.

Validation should explicitly confirm that the current WING detections reconstructed from the instrumented windows match the unmodified production detector for sampled files. If there is any mismatch, stop the comparative analysis and diagnose it first.

## After the FSD run: analysis, not tuning

Once both feature tables are available, produce a research summary comparing the xeno-canto corpus with the FSD hard negatives. Do **not** change thresholds and do **not** train a production classifier yet.

Because the xeno-canto labels are weak, separate these questions carefully:

1. Which measurements distinguish **current-WING candidates in wingbeat-containing xeno-canto recordings** from current-WING candidates in known environmental hard negatives?
2. Which current gates/features appear uninformative because strong FSD hard negatives satisfy them just as well?
3. Which new features look promising for separating footsteps/running, applause, clocks, machinery, rain/wind, etc. from plausible wingbeats?
4. Are there obvious dataset/source artifacts (MP3 vs WAV, amplitude normalization, sample-rate/codec effects, uploader/source effects) that could create false separation?
5. Which xeno-canto recordings can safely become stronger positive examples based on metadata such as a recording type consisting only of `wingbeats`, short duration, or explicit timestamps/remarks? Keep this as a proposed curation strategy unless the audio/metadata supports exact localization.

For each promising feature, show distributions/effect sizes rather than only p-values. Prefer robust summaries (median, IQR, quantiles) and inspect class overlap. If you test simple models, use them only diagnostically and clearly prevent source leakage; do not integrate a model into WING yet.

## Deliverables back to me

At the end, give me:

1. A concise description of exactly what code/files you added or changed.
2. Test results proving production WING decisions were not changed.
3. Confirmation of the FSD hard-negative run: files processed, windows measured, detections, errors, and validation mismatches if any.
4. A ranked-by-evidence **research findings list**, not a proposed production threshold rewrite: which existing/new measurements appear most and least useful, with numbers.
5. Any data-quality or source-bias problems you found.
6. A recommendation for the *next experiment* needed before modifying WING (for example, manual temporal annotation of a stratified subset of xeno-canto positives, addition of xeno-canto insect negatives, or collection of real NFC false positives).
7. Paths to all generated CSVs/reports so I can find them.

Do not commit or push unless I explicitly ask. Do not delete or overwrite the original FSD50K audio or my existing WING code/data.
