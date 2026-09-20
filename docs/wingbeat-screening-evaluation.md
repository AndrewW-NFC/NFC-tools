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
