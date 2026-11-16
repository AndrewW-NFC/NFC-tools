# Experimental preflight buzz screening

The existing three-second saved sample is screened after it passes the input
level check. A match changes that check to an advisory beside the existing audio
player. It does not block recording. A negative result or screening failure adds
no user-facing text. Failures are logged; measurements and thresholds are appended
to the sample's downloadable diagnostics log. Running preflight again replaces
all previous results through the existing page flow.

The original detector targets the broad buzz found in three user-supplied clips,
not every kind of electrical hum. It does not diagnose grounding problems.

## Broad-buzz persistence and strength rule (retained from v2)

Version 3 decodes to mono at 48 kHz using the existing ffmpeg dependency
(v2 used 8 kHz). Analyze one-second
Hann windows at quarter-second steps, including a final window aligned with the
end of the sample. Require all windows to satisfy all three conditions:

- Mean spectral density at 800–1,400 Hz exceeds that at 1,600–2,400 Hz by 6 dB.
- Effective occupied bandwidth in the target band is at least 80 Hz, rejecting
  narrow tones (squared sum of bin powers divided by sum of squared bin powers;
  frequency bins are 1 Hz apart).
- Target-band RMS is at least -60 dBFS, rejecting negligible band energy even
  when unrelated frequencies are loud. Power is normalized for Hann-window energy.

Also require the median window excess to be at least 9 dB. This conservative
strength gate reduces warnings from modest persistent spectral coloration; the
6 dB gate still requires the pattern throughout the sample. Both measurements
and thresholds are logged with detector ID `persistent_buzz_v3`, alongside the
harmonic-screen measurements.

The frequency ratio is gain-independent. Requiring every window is intentionally
conservative: masking can cause missed detections. Persistence is evaluated at
one-second resolution; this is not proof that noise is present at every instant.

## Initial local evaluation — October 8, 2026

Six original WAV clips from the same microphone and site were used to explore
these features and then evaluate the prototype. The recordings remain on the
user's external drive and are not included in the repository.

| Date | Clip | Full-clip advisory | Three-second excerpts flagged |
| --- | --- | --- | --- |
| 2026-10-07 | Parulidae (0.891) | Yes | 13 / 13 |
| 2026-10-07 | Passeriformes (0.96) | Yes | 14 / 14 |
| 2026-10-07 | ZEEP (0.849) | Yes | 13 / 13 |
| 2026-10-06 | Parulidae (0.937) | No | 0 / 13 |
| 2026-10-06 | Passeriformes (0.861) | No | 0 / 14 |
| 2026-10-06 | savspa (0.998) | No | 0 / 14 |

Excerpts start every half second, retaining only complete three-second excerpts.
These overlapping excerpts are not independent validation examples. All six
source clips informed feature selection; results do not establish accuracy on
unseen recordings or other devices. Further clean/noisy field examples are needed
before broadening the detector. Synthetic tests cover steady broad noise at
several gains, silence, faint noise, narrow tones, brief and interrupted noise,
endpoint coverage, and advisory/diagnostic integration.

## False-positive correction — October 14, 2026

The user identified `readiness_test_20261013-182810_sounddevice.wav` as normal.
The unchanged v1 detector nevertheless flagged all nine windows: excess ranged
from 6.27 to 7.33 dB (median 6.96 dB). Normal audio can satisfy that rule, so v2
adds the 9 dB median requirement. This is a local recalibration using a new
negative example, not independent evidence of general accuracy. It deliberately
trades sensitivity to weaker buzz for fewer false advisories.

Rechecked the original noisy clips in `2026-10-07/clips/20-49-37` and clean clips
in `2026-10-06/clips/03-00-00` on the external drive:

| Date | Clip | v2 full-clip advisory | v2 three-second excerpts flagged |
| --- | --- | --- | --- |
| 2026-10-07 | Parulidae (0.891) | Yes | 7 / 13 |
| 2026-10-07 | Passeriformes (0.96) | Yes | 14 / 14 |
| 2026-10-07 | ZEEP (0.849) | Yes | 13 / 13 |
| 2026-10-06 | Parulidae (0.937) | No | 0 / 13 |
| 2026-10-06 | Passeriformes (0.861) | No | 0 / 14 |
| 2026-10-06 | savspa (0.998) | No | 0 / 14 |
| 2026-10-13 | Readiness sample | No | 0 / 1 |

The actual readiness assessment of the October 13 WAV now returns `ready`, with
playback retained. The source recording and its original log were not modified.
Synthetic regression controls cover modest spectral coloration at several gains,
strong broad buzz, decoder/readiness integration, and low-frequency FFT leakage.
The band-level floor prevents numerical leakage from loud low-frequency tones
from masquerading as broad buzz. That version remained a broad-buzz heuristic, not a
50/60 Hz mains-hum detector; a negative result did not rule out electrical noise.


## Harmonic-line correction — November 16, 2026 (v3)

The user reported audible buzzing and evenly spaced spectrogram lines in
`readiness_test_20261115-165446_sounddevice.wav` after leaving the laptop ungrounded.
Its original log confirms v2 ran but did not flag it: window excess ranged from
-6.94 to +2.49 dB, with a median of -1.46 dB. It failed the broad-band shape rule.
The persistent lines are especially clear above 10 kHz, which the old 8 kHz
resampling discarded. The sample does not establish the electrical cause.

The new second path uses the same one-second Hann windows and quarter-second
steps, including the final endpoint. It searches 2–20 kHz (or below Nyquist for
lower-rate direct callers). A line must exceed the median neighboring power by
6 dB and have single-bin RMS of at least -85 dBFS in every window. Neighbor bins
are 5–20 Hz away on either side; adjacent qualifying bins within 4 Hz are
collapsed to one line, choosing the strongest minimum power across windows.

At least 12 persistent lines must fit integer multiples of a common spacing
between 50 and 300 Hz, within 2 Hz of each multiple. Matched lines must span at
least 2 kHz and account for at least 60% of the persistent lines. Spacings are
searched in 0.01 Hz steps; ties select the largest spacing. This avoids reporting
an arbitrary subharmonic when an equally good larger spacing exists. These
thresholds are engineering choices, not established boundaries for electrical noise.

Either the retained broad-buzz rule or this harmonic rule produces the existing
advisory. Diagnostic JSON includes `broad_buzz_match` and `harmonic_screening`,
including thresholds, persistent/matched line counts, and fitted spacing. A
negative result still adds no buzz message. Volume checks are unchanged: a peak
of 0 dBFS alone does not warn.

Manual replay of the reported original WAV through the complete saved-sample
assessment now returns `note`, with 36 persistent lines, all 36 aligned at
114.74 Hz spacing. The broad-buzz path remains negative. The original WAV and
log were not modified or added to the repository. This is a development example,
not an independent validation set. The older external-drive recordings were not
available for replay during this change.

Synthetic regressions cover high-frequency harmonic buzzing under louder
low-frequency background at several gains, fractional sample duration, random
nonharmonic persistent tones, one tone, brief/interrupted buzzing, faint lines,
and background noise. Decoder/readiness/logging integration is tested for both
paths. The level-check regression also confirms a 0 dBFS peak remains ready.
Existing broad-buzz and modest-coloration controls remain in place.

This screen can miss weaker, drifting, masked, or lower-frequency interference.
Persistent harmonic sounds from other sources may also trigger the advisory.
It does not identify grounding faults, guarantee clean audio, or change WING or
bird-call analysis; listening remains necessary.
