# Experimental preflight buzz screening

The existing three-second saved sample is screened after it passes the input
level check. A match changes that check to an advisory beside the existing audio
player. It does not block recording. A negative result or screening failure adds
no user-facing text. Failures are logged; measurements and thresholds are appended
to the sample's downloadable diagnostics log. Running preflight again replaces
all previous results through the existing page flow.

The initial detector targets the broad buzz found in three user-supplied clips,
not every kind of electrical hum. It does not diagnose grounding problems.

## Persistence rule

Decode to mono at 8 kHz using the existing ffmpeg dependency. Analyze one-second
Hann windows at quarter-second steps, including a final window aligned with the
end of the sample. Require all windows to satisfy all three conditions:

- Mean spectral density at 800–1,400 Hz exceeds that at 1,600–2,400 Hz by 6 dB.
- Effective occupied bandwidth in the target band is at least 80 Hz, rejecting
  narrow tones (squared sum of bin powers divided by sum of squared bin powers;
  frequency bins are 1 Hz apart).
- Window RMS is at least -60 dBFS, rejecting negligible input.

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
