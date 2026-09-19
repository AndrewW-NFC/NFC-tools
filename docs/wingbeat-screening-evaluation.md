# Experimental wingbeat detector evaluation

## Known-positive recording

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

## Synthetic controls

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
