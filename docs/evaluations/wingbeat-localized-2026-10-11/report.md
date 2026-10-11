# Localized upper-frequency WING pulses — October 11, 2026

## Change and rationale

The user identified wingbeat passages beginning at 17:58 and 42:00 in
`012_NFC_2026-10-11_03-00-00.wav`, and a faint detected passage beginning at
24:48. All times are elapsed recording times. The original detector found
repetition in the missed passages but rejected their spectral support.

At 18:03.50–18:05.00, repetition was 0.958 and residual coherence 0.966,
but pulse-excess flatness was 0.0126 (<0.30), bass fraction 0.000666
(<0.005), and ridge prominence 3.68 (<16). At 42:04–42:06, all common
and flatness checks passed; only bass-or-prominent-ridge support failed.
The faint detection at 24:49.50–24:51.00 passed through the 3500–6500 Hz
accompaniment route, and required the 1.5-second pass. Its bass fraction
0.0101 helped it pass, although the source of that bass is not established.

The new acceptance alternative looks for a **bounded broad lobe in the
pulse-on minus pulse-off power spectrum**, instead of requiring bass or a
sharp whistle. It keeps all existing detections and all common accompaniment
checks. Additional requirements are:

- Search band starts at 3500 Hz or above.
- At least six pulses; repetition >=0.60 and second-repeat correlation >=0.50.
- Residual coherence >=0.80 and contrast >=0.25.
- Ridge/frame-maximum power fraction >=0.01.
- Quarter-height pulse-lobe width 500–3000 Hz, with both edges inside
  300–10000 Hz. Nine-bin smoothing tolerates fine spectral texture; the lobe
  peak must be within eight FFT bins of the tracked median maximum.
- Unsmoothed inverse-participation width of at least 400 Hz inside that lobe.
  This rejects apparent bandwidth supplied by smoothing a few thin peaks.

The original spectral alternative, rhythm thresholds, window schedule,
broadband detector, output format, and confidence semantics are unchanged.
The new route does not use the relaxed near-miss rhythm thresholds. It adds
no runtime dependencies and retains bounded two-second audio buffering.

For example, the new route measures a 750 Hz lobe with 523 Hz effective
width at 18:03.25–18:05.25, and a 2203 Hz lobe with 1487 Hz effective width
at 42:04.75–42:06.75. These thresholds were developed using the supplied
positives, not independently validated biological limits.

## Measured results

Full hour: **3600 seconds**.

| Screen | Merged intervals (minutes:seconds) |
|---|---|
| before | 24:49.50–24:51.00 |
| after | 17:59.25–18:07.25; 24:49.50–24:51.00; 42:04.50–42:07.25 |

| Available field set | Before | After |
|---|---:|---:|
| positive | 10/11 | 10/11 |
| discrete-negative | 0/11 | 0/11 |

| Gain/alignment variants overlapping each passage | Before | After |
|---|---:|---:|
| 1758 | 0/12 | 12/12 |
| 2448 | 12/12 | 12/12 |
| 4200 | 0/12 | 12/12 |

The full suite passed **851 tests, with 3 platform skips**. This includes 53 new
localized-pulse controls and the existing call-rejection, high-pass noise,
whistle, timing, and broadband controls. Ruff F checks, compilation, version
consistency, dependency consistency, and diff whitespace checks also passed.
The field comparison made 236 production-decision agreement assertions across
118 jobs; all passed. Every previously accepted window was retained.

Results: [summary and source hashes](summary.json),
[per-file intervals and PCM/source hashes](per-file-results.csv), and
[newly accepted full-hour windows and features](recovered-windows.json).

The full hour contains no additional detections outside the three supplied
passages. The previously missed bufflehead clip remains missed. Variant overlap
checks use audit neighborhoods 1078–1089, 1488–1493, and 2520–2530 seconds;
these are not user-supplied exact event endpoints.

## Reproduction

From the repository root, with an editable installation and the source audio:

```sh
.venv/bin/python docs/evaluations/wingbeat-localized-2026-10-11/run.py \
  '/Volumes/T7/NFC recordings/2026-10-10/audio/012_NFC_2026-10-11_03-00-00.wav' \
  --positives '/Volumes/T7/Wingbeats detector/Confirmed species wing sounds' \
  --negatives '/Volumes/T7/Wingbeats detector/wav files with false positive WING sounds.zip' \
  --output /tmp/nfc-localized-evaluation
.venv/bin/python -m pytest -q
```

`run.py` decodes mono float32 PCM at 24 kHz, records PCM and corpus source
hashes, and uses the production window iterator. Full-hour jobs own disjoint
60-second start ranges with two seconds of lookahead; detections merge across
job boundaries. Baseline decisions disable only the new spectral alternative
by zeroing its two measurements. The unchanged broadband predicates are
shared with the existing research helper. Two windows per job are checked
against production `screen_window`.

Separately, all original accompaniment feature values and baseline decisions
were checked for exact equality against the unmodified source on 15 field
windows, under both strict and near-miss rhythm settings. The baseline Git
revision is `b19422b45b138b2208a9b2c4f007f0f5dc93097e`.

Variants use 24-second crops starting at 17:52, 24:42, and 41:54, with gains
0.1/1/3 crossed with leading silence 0/0.25/0.5/0.75 seconds. These correlated
transformations test sensitivity to gain and alignment; they are not
independent recordings. Audio and saved production results are never modified.

## Scope and limitations

The three field labels are supplied by the user. Candidate intervals indicate
screening support, not precise wingbeat onset/offset or species identity.
Available older field material includes eleven confirmed-species recordings
and eleven discrete-sound negatives. The historical 47 osprey/other-call clips,
two bat clips, rain/insect recordings, and wind/cricket caches could not be
recovered in the October 10 audit and remain unavailable here. Synthetic call,
noise, and spectral-support controls do not replace those field negatives.

The stricter temporal and bandwidth requirements guard the new alternative,
but localized insect, mechanical, or other repeating noise may still resemble
wingbeats. This development-set evaluation does not establish general field
precision or recall. Changes outside the three labeled passages, if any, must
be treated as unclassified rather than automatically false positives.
