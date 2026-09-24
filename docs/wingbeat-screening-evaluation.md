# Experimental wingbeat detector evaluation

## Earlier evaluation, before the cross-band refinement

The positive-recording and synthetic counts in this section describe the earlier
detector. See the September 20 evaluation below for current results.

### Known-positive recording

The supplied `654426482.wav` is approximately 13.99 seconds long. The original
four-second-window detector produced no candidates. Its 6–10 second window had
amplitude modulation 0.436, below the old 0.45 cutoff, despite repetition
correlation 0.686. The amplitude gate prevented the later checks from running.

The revised detector produces one merged `WING` review interval at **5–9 seconds**.
This is a screening interval, not a claim about exact wingbeat onset/offset.
The 5–7 second window scores 0.781 for repetition and 0.651 at twice the period;
the 7–9 second window scores 0.672 and 0.525. Neither score is a probability.

Gain multipliers of 0.1, 1, and 3 and leading padding of 0, 0.25, 0.5, and 0.75
seconds all retain a positive result (12/12 variants). Window alignment changes
the reported interval slightly. These are variants of one recording, not 12
independent recordings. The earlier positive MP3 was unavailable at its supplied
path for this evaluation and was not retested.

### Synthetic controls

For each class, 100 seeded four-second examples were passed through the streaming
detector. The counts below mean examples with at least one candidate interval.

| Example class | Flagged / 100 |
| --- | ---: |
| Regular broadband pulse trains | 100 |
| Low-contrast pulse trains against background noise | 100 |
| Pulse trains with modest timing variation | 100 |
| Steady white noise | 0 |
| Pink noise | 0 |
| Low-frequency-weighted noise | 0 |
| Single broadband loudness swell | 0 |
| Modulated pure tones | 0 |
| Sweeping tones | 0 |
| Sweeping tonal calls with background noise | 0 |
| Random clicks | 1 |

The random-click false positive is retained in this report. These controls are
simplified signal models; low-frequency-weighted noise is not a representative
field wind dataset. Rhythmic machinery, rain, and other repeated broadband sounds
can resemble wingbeats. These measurements do not establish field precision or
recall, species coverage, or reliability on a full night of recordings.

## Reproduce

From an editable installation:

```bash
python scripts/evaluate_wingbeats.py /path/to/known-wingbeats.wav
pytest -q tests/test_wingbeats.py
```

The evaluation script reads the supplied file without modifying it and decodes it
into memory for the gain/alignment checks. The production analyzer streams audio
in bounded windows. No user recording is included in the repository.

The next evaluation should use manually marked positive and negative intervals
from longer recordings at the actual site, including rain, insects, calls,
handling sounds, and mechanical noise. Tune on one subset and assess a separate
held-out subset before making field-accuracy claims.

## September 20, 2026: 31 supplied false-positive clips

The user labeled all 31 WAVs in `31 WINGs.zip` as false positives and reported
frequent cricket sounds, without identifying individual sources. The recordings
total 314.028 seconds. All 31 reproduce a detection under the earlier gates
(33 accepted two-second windows). The new cross-band requirement leaves **6/31**
clips flagged and suppresses **25/31 (80.6%)**. This is a development-set result:
the recordings informed the change and are not an independent holdout.

The earlier spectral-flatness test can pass a narrowband pulse train mixed with
broadband background noise. The added test measures whether the amplitude
modulation repeats together in at least three of four disjoint frequency bands:
150–600, 600–1200, 1200–2000, and 2000–3000 Hz. A qualifying band must correlate
with the full-band envelope by at least 0.60, repeat at the same selected lag by
at least 0.35, and have modulation of at least 0.15. Existing screening gates
remain in place. These are provisional engineering cutoffs.

Six user-labeled false positives remain; their repeating energy passes the
broader-band check. They have not been relabeled as genuine wingbeats:

- `WING (review required)-Wingbeats.wav`
- `WING (review required)-Wingbeats 4.wav`
- `WING (review required)-Wingbeats 6.wav`
- `WING (review required)-Wingbeats 7.wav`
- `WING (review required)-Wingbeats 3 2.wav`
- `WING (review required)-Wingbeats 5 2.wav`

The 100-seed synthetic sweep retains all 100 regular, all 100 low-contrast, and
all 100 jittered broadband pulse trains. Random clicks still produce 1/100
flagged examples; each other negative class remains at 0/100. Regression tests
also cover pulsed tones in broadband noise at seven carrier frequencies,
including sub-band boundaries, and broadband pulses with a tonal background.

The earlier known-positive `654426482.wav` could not be found for this update.
Its historical 5–9 second detection and gain/alignment results above have **not**
been verified with the cross-band gate. Genuine field positives are needed to
measure any sensitivity loss, especially for spectrally restricted wingbeats.
No claim is made about insect species or field precision/recall.

Reproduce the negative-batch comparison with:

```bash
python scripts/evaluate_wingbeat_negatives.py '/path/to/31 WINGs.zip' --output /path/to/report
```

The script accepts a ZIP or WAV directory, excludes macOS metadata, and records
per-file SHA-256 hashes, durations, baseline/current intervals, and per-window
features in CSV and JSON reports. It decodes each clip into memory; production
analysis remains bounded to overlapping windows. No supplied audio is committed.


## September 20, 2026: whistle plus surrounding-noise experiment

The subsequent positive set contains 12 recordings (11 MP3, one WAV; 77.220 s),
labeled by the user/filenames as waterfowl, mourning dove, and double-crested
cormorant. It revealed that the earlier broadband gate misses genuine tonal
wing sounds. The supplied positives and all 31 negatives were used during this
experiment; neither set is a held-out validation set.

| Screen | Known-positive clips flagged / 12 | Known-negative clips flagged / 31 |
| --- | ---: | ---: |
| Original screen | 4 | 31 |
| Three-band refinement | 3 | 6 |
| Broadband OR pulse-linked accompaniment | 10 | 6 |

The added path recovers bufflehead, common goldeneye 2, both mallards, mourning
dove, and both mute swans, while retaining cormorant, long-tailed duck and
white-winged scoter. The short common goldeneye and wood duck recordings remain
unflagged. In the short goldeneye example, the residual measurement does not
reliably rise with the whistle; wood duck has insufficient measured periodicity
and surrounding-energy contrast. These are limitations of the measurement,
not evidence that the user's positive labels are incorrect.

Production now decodes at 24 kHz. The added path searches spectral maxima across
four overlapping bands up to 9.5 kHz and measures nearby residual energy up to
10 kHz. Strong ridges, including harmonics, are masked with guard bins. It tests
whether the softer residual envelope is correlated with the repeating ridge
and louder during ridge pulses than between pulses. See README_DEV for the
exact provisional thresholds. The broad-pulse path remains an alternative.

Leakage controls matter: the first prototype could flag remote, very faint
side-lobes of a pure tone. A minimum ridge/whole-frame power ratio rejects these.
A second regression appeared when the old low-band path saw minute spectral
leakage from a high-frequency sweep; a low-band/total-energy floor now guards
that path. Off-bin tones, harmonics, stationary backgrounds, high-frequency
sweeps, synchronous softer noise and anti-phase residual envelopes are covered
by regression tests. Matching pulse timing does not establish aerodynamic origin.

The accompaniment path alone accepts 10/12 positives and 0/31 negatives in the
final corpus run. The combined detector retains the six broadband false
positives; it does not relabel them. Wider frequency coverage and the ridge
rhythm measurement contribute to the gain. The new path's rhythm gates already
reject these 31 negatives, so this corpus does not independently demonstrate
that the residual-noise requirement separates insects. Synthetic controls test
that requirement by holding tone timing constant and changing its accompanying
noise. No precision/recall, species-coverage or general field-accuracy claim is
supported by this small development corpus, and clip-level hits do not validate
exact wingbeat boundaries.

The batch evaluation command now supports WAV/MP3 folders and ZIPs and compares
all three screens. It records 8 kHz historical window features and 24 kHz
accompaniment diagnostics, hashes, and per-file intervals. For example:

```bash
python scripts/evaluate_wingbeat_negatives.py '/path/to/Known positive wingbeats' --output /path/to/positive-report
python scripts/evaluate_wingbeat_negatives.py '/path/to/31 WINGs.zip' --output /path/to/negative-report
pytest -q tests/test_wingbeats.py tests/test_wingbeat_accompaniment.py tests/test_importer.py
```

The existing `evaluate_wingbeats.py` now exercises the production 24 kHz path
for its synthetic and gain/alignment checks. The 8 kHz default of internal
screening functions is retained for older broadband callers.


Final verification: 363 Python tests pass. At the production rate, the 100-seed
sweep retains all 300 synthetic positive examples. Of the synthetic negatives,
white/pink/low-frequency-weighted noise, random clicks, modulated tones, sweeping
tones and tonal calls with noise each flag 0/100. Single swells flag **1/100**;
this remaining false positive is recorded rather than hidden. Sample generation
now uses 24 kHz, so seeded noise waveforms are not identical to the historical
8 kHz controls above. New tests also verify real high-frequency WAV decoding,
streaming, soft accompaniment, low-frequency background and leakage rejection.


## September 20, 2026: stable surrounding-noise regions

The 14 subsequent Merrill Lake negatives expose a measurement confound in the
moving-region version (`a56e4a6`): between pulses, the selected maximum can jump
from a whistle to another background frequency, and the surrounding-noise
measurement moves with it. An uneven but stationary background can then look
pulse-linked. All 14 new negatives reproduce through the 6–9.5 kHz accompaniment
band, and none passes the broadband route.

The updated accompaniment path anchors residual regions and their lower/upper
split to the median ridge bin for each window. The tone still follows its
per-frame peak, and strong-tone/harmonic masks still apply per frame inside the
fixed region. Thresholds and offsets are unchanged; diagnostics now include
`noise_center_hz`. Regions may differ between windows, but not between frames
within one window. This does not guarantee that every usable residual bin stays
constant, because harmonic masks are still dynamic.

| Set | Moving regions | Stable regions |
| --- | ---: | ---: |
| Known positives | 10/12 | 10/12 |
| Earlier negatives | 6/31 | 6/31 |
| New Merrill Lake negatives | 14/14 | 2/14 |
| All supplied negatives | 20/45 | 8/45 |

These are development-set clip-level hits. The remaining new negatives are
Wingbeats 2 and Wingbeats 13. The stable version recovers the short common
goldeneye but loses common goldeneye 2; wood duck remains missed. Identical
positive totals do not mean identical sensitivity. Alternatives anchored only
to the loudest frames or to mean spectral power detected 9/12 positives, so the
all-frame median was retained. No thresholds were relaxed to recover the lost
example. The fixed-region measurement is a correction to the identified
confound, not evidence of a universal wingbeat/insect distinction.

Gain multipliers 0.1, 1 and 3 combined with leading padding 0, 0.25, 0.5 and
0.75 seconds were checked for every positive. Both goldeneye outcomes persist
through all 12 variants. Bufflehead is detected in 9/12 variants and long-tailed
duck in 6/12 under both versions; the other previously detected species remain
at 12/12. Wood duck remains at 0/12. These are correlated variants of the same
12 recordings, not additional independent field examples.

Forty regression cases exercise a 6.1 kHz pulsed tone with shaped background
noise above or below it. Stationary noise stays rejected across five seeds and
three noise levels; the same shaped noise pulsed in synchrony is retained.
The previous moving-region implementation failed the stationary-noise controls.


Final verification: **403 Python tests pass**, with two existing dependency
deprecation warnings. Compilation, changed-code lint and diff whitespace checks
pass. The 100-seed sweep retains all 300 synthetic positives. Synthetic negatives
remain unchanged: 1/100 single swells flags; white/pink/low-frequency-weighted
noise, random clicks, modulated tones, sweeping tones and tonal calls with noise
each flag 0/100. This remaining synthetic false positive is included in the result.

## September 24, 2026: confirmed cricket-only clip near 3.5 kHz

The user confirmed no wingbeats in the 9.813-second `ZEEP (0.963)-Nighthawk_01.wav`
and marked cricket sequences at 3.20–3.90, 5.15–5.65 and 7.40–8.20 seconds.
Using its previously decoded 24 kHz mono cache (the original was no longer at
its supplied path), the current detector returns no candidates. All 12 gain
and leading-padding combinations (0.1/1/3 gain; 0/0.25/0.5/0.75 seconds padding)
and all 89 overlapping windows starting every 0.1 seconds are also rejected.
Windows contain up to two seconds, with at least one second remaining.
These are variants of one recording, not independent validation examples.

The 3–5, 5–7 and 7–9 second windows fail both repetition and synchronized
surrounding-noise gates in the 1.8–4 kHz search band. No WING false positive
was reproduced, so detector behavior and thresholds were preserved. A source
recording with its WING-exported interval is needed to investigate a contextual
false positive further. Recordings remain outside the repository.

The evaluation script now accepts a single WAV/MP3 as well as a ZIP or folder.
Its CSV shows readable time intervals and `None detected` instead of empty JSON
arrays, with UTF-8 BOM encoding. Structured JSON results remain unchanged.

## September 24, 2026: wind false positive and broadband detrending

The supplied `WING (review required)-Wingbeats_01.wav` (10.069 seconds), described
by the user as a wind false positive, reproduces a broadband-path candidate at
4–6 seconds. Its repetition scores were 0.691 and 0.610 at one and two lags,
with three coherent bands. The accompaniment path did not accept this clip.

Subtracting a 510 ms symmetric running mean from the broadband envelope and each
sub-band envelope before repetition/coherence checks lowers the 4–6 second
scores to 0.186 and 0.088, with zero coherent bands. Raw amplitude and modulation
gates remain unchanged, as do thresholds and the accompaniment path. This applies
the same slow-trend removal already used for accompaniment to the broadband path.
It addresses correlation caused by gradual loudness changes; it is not a general
wind classifier. Historical evaluation explicitly disables detrending so its
original and cross-band columns continue to describe their frozen gates.

| Cached recording group | Before flagged | After flagged |
| --- | ---: | ---: |
| Known positives | 10/12 | 10/12 |
| Earlier false positives | 6/31 | 0/31 |
| Merrill false positives | 2/14 | 2/14 |
| Confirmed cricket-only clip | 0/1 | 0/1 |
| New wind clip | 1/1 | 0/1 |

The same positive clips are retained: common goldeneye 2 and wood duck remain
missed. Across gains 0.1/1/3 and leading padding 0/0.25/0.5/0.75 seconds, all
144 positive-variant detection decisions are unchanged. Bufflehead is detected
in 9/12 variants and long-tailed duck in 6/12; the other eight detected positive
clips pass all 12 variants. The wind clip falls from 6/12 to 0/12 variants.
These are development-set results, not independent field accuracy estimates.

The original wind WAV was successfully decoded at the start of this analysis
but was absent at a later access. Subsequent checks use its preserved 24 kHz mono
cache. Audio remains outside the repository. Regression tests cover gradually
increasing random noise at 8/24 kHz and genuine 3/7/12/18 Hz pulses under the same
trend. Exactly 2 Hz pulses in two-second windows fail in both the earlier and
revised screen; the advertised approximate lower rhythm bound is not guaranteed.

The 100-seed synthetic sweep retains all 300 regular, low-contrast and jittered
positive examples. Each negative class yields 0/100 except a single swell at
1/100. All 205 WING tests pass. The full suite has 440 passes and two eBird
failures, both reproduced from an unchanged archive of HEAD (253c1f5).

## September 24, 2026: distinct pulse counting

Broadband and accompaniment screens now count one peak per continuous
above-threshold region, then retain peaks in descending amplitude order only
when separated by at least 60% of the selected repetition period. This prevents
closely spaced shoulders or threshold recrossings within one sound from
satisfying the existing minimum of four pulses. The period-relative spacing is
provisional; it allows timing variation rather than requiring exact spacing.
All other gates and thresholds remain unchanged. Historical broadband evaluation
with `detrend=False` retains its original threshold-crossing pulse counter.

The final counter cannot increase the number of pulses relative to the previous
counter, so it cannot create new accepted windows. Tests cover three versus
four double-peaked broadband events at 8/24 kHz, accompanied whistles, one
continuous noisy swell, and events touching the window boundaries.

| Development set | Before flagged | After flagged |
| --- | ---: | ---: |
| Earlier confirmed positives | 10/12 | 10/12 |
| New development positives | 6/8 | 6/8 |
| Discrete-sound negatives | 4/11 | 2/11 |
| Original noise/insect negatives | 0/31 | 0/31 |
| Merrill insect negatives | 2/14 | 2/14 |
| Individual wind and cricket examples | 0/2 | 0/2 |

Discrete clips 6 and 7 are now rejected; 5 and 9 remain flagged. The same positive
misses remain: older common goldeneye 2 and wood duck, plus the newer bufflehead
and common merganser. Across 20 development positives and four leading-padding
values (0, 0.25, 0.5 and 0.75 seconds), all 80 detection decisions are unchanged.
These selected recordings do not establish field accuracy or calibrated confidence.

Common loon, great blue heron and ruddy duck were reserved from development.
They were first scored after fixing a provisional algorithm but while synthetic
validation was still running. That validation exposed a swell regression in the
provisional local-maximum counter. It was corrected by collapsing continuous
above-threshold regions before spacing peaks; reserved outcomes were not used to
choose the correction. Nevertheless the final retest must not be described as
an untouched holdout. Future independently labeled nights are needed.

The intended practical scope is larger birds with prominent wing sounds.
No claim of reliable shorebird or passerine coverage is made. WING remains a
manual-review screen without species identification or probability estimates.

The final reserved retest matches the previous detector: common loon is flagged
at 1–5 and 6–8 seconds (overlapping its 2–10-second annotation), great blue heron
at 4–12 seconds (within its 3.5–13-second annotation), and ruddy duck is missed.
These are clip/window detections, not proof of exact event attribution.

The final 100-seed synthetic sweep detects all 300 regular, low-contrast and
jittered positive examples and rejects all 800 negative controls across eight
classes (including the single-swell class). All 233 WING tests pass. The full
suite has 468 passes and the same two previously reproduced eBird failures.
No recordings were committed; no detector confidence probability is claimed.
