# American Robin trigger diagnosis — November 6, 2026

The supplied clips reproduce false positives through spectral accompaniment,
not the broadband route. This is a completed trigger diagnosis, not a validated
robin rejection rule. Production detector code is unchanged.

## User-defined split

Source: `robin training.zip`; its SHA-256 and detector revision are recorded in
`results.json`. Descriptive names without “faint” are diagnosis clips; names
beginning `WING (review required)` are varied development clips. Six audio files
containing “faint” were excluded without decoding. PKF waveform caches and
macOS metadata were ignored. The user's separately held-back 10–20 clips were
not accessed. Labels come from the user; this analysis does not independently
identify every sound, particularly in mixed-species clips.

| Set | Clips | Duration | Clips triggering WING | Accepted windows |
|---|---:|---:|---:|---:|
| Diagnosis | 7 | 67.67 s | 7 | 13 |
| Varied development | 34 | 229.48 s | 26 | 112 |

A window is not an independent call or recording. Multiple search bands can
accept the same window. These curated counts do not estimate field accuracy.

## Trigger mechanism

All 125 accepted windows fail the broadband-flapping route. All accepted
accompaniment features meet the ordinary/conditional rhythm route; none needs
the irregular-rhythm alternative. Disabling the irregular-rhythm recovery
would therefore not fix these examples.

The diagnosis clips expose two acceptance mechanisms:

- The four `cheep` files pass spectral support in the 3.5–6.5 kHz search band.
  Their tracked residual centers are approximately 4.20–4.38 kHz. Four counted
  pulses, a prominent spectral ridge, and nearby energy synchronized with the
  pulses satisfy the current gates. These are feature measurements, not a
  claim that every tracked ridge is the fundamental call frequency.
- `busy.wav` and `hisselly.wav` pass the localized-lobe alternative, with seven
  counted pulses and effective lobe widths about 836 and 875 Hz. Their centers
  are about 4.50 and 4.62 kHz. Rejecting thin tonal calls alone would miss them.
- `mixed with jays.wav` passes spectral support with a center near 3.14 kHz.
  Its mixed-species label means the trigger should not automatically be
  attributed to the robin alone.

The varied set is broader: 41 accepted band/window records use spectral support
and 77 use localized support, spanning tracked centers around 1.17–6.75 kHz.
A single narrow frequency exclusion would not cover this development set.

Current “nearby noise” measurements can describe a vocalization's own energy.
Synchronization and measured spectral breadth do not independently establish
that a pulse is aerodynamic. Any future rejection feature needs to distinguish
that structure while retaining true wing pulses, including wings with calls.

## Overlapping excerpts and non-reproducing clips

Exact decoded-PCM hashes confirm shared accepted windows between:

- `cheep and chup prominent.wav` and `cheep and chump prominent 2.wav`;
- `cheep mixed.wav` and `cheep mixed 2.wav`;
- WING clips 17/18, 22/23, and within 45/46/47.

These relationships should remain grouped during any later split. No accepted
window hash matched across the diagnosis and varied groups, but that does not
prove independent recording sessions or absence of other overlap.

WING clips 11, 12, 15, 25, 28, 29, 33 and 38 do not trigger in a standalone scan
of their supplied crop. They are not counted as successful suppression. Cropping
can alter analysis alignment/context; detector version or export processing may
also matter. The cause is not established without the original source context.

## Rejected shortcut

Every diagnosis trigger has little measured 150–600 Hz energy relative to
150–3000 Hz: approximately 0.0055%–0.0194%. Imposing the existing 0.5% bass
threshold on *every* accompaniment route would change the diagnosis count from
7 to 0 and the varied count from 26 to 4 (44–47 remain).

However, this also changes the existing synthetic localized-pulse positive
controls from 15/15 accepted to 0/15. These controls deliberately represent the
no-bass pulse shapes the localized route is intended to retain. They are not
15 independent field recordings. The shortcut was rejected, not implemented.
See `bass-veto-counterexample.json` and its reproducer.

## Verification and next decision

Two complete streaming runs yielded identical intervals. Diagnostic accepted
windows reconstruct all production intervals exactly. Both use production
FFmpeg decoding to 24 kHz mono, the complete 1/1.5/2-second window schedule,
and production feature/acceptance helpers. Source audio was not modified or
copied into the repository. File hashes, excluded names, intervals and accepted
features are retained in `results.json`; `clips.csv` is a compact index.

The next useful development step is a feature-level call/pulse separation
experiment, with explicit retention checks for real wingbeats and overlapping
calls. The broader field regression corpus on T7 was unavailable during this
analysis. A production rejection rule has not yet been justified. Keep the
held-back clips untouched until a candidate and its thresholds are frozen;
then evaluate by recording/session rather than overlapping excerpts.

## Reproduction

From the repository root:

```sh
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-06/diagnose.py '/path/to/robin training.zip' --output /tmp/robin-diagnosis
.venv/bin/python docs/evaluations/wingbeat-robin-2026-11-06/check_bass_veto.py /tmp/robin-diagnosis/results.json
```

Current extracted audio location: `/Volumes/T7/Wingbeats detector/audio-library/robin-training/`
(the additional set is under `Test against/`). The ZIP commands above describe
the original input; use the exclusion report’s verifier for the current layout.
