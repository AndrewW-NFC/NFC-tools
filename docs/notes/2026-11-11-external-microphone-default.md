# External microphone selection

Approved as a bug fix on November 11, 2026. The November 10 session recorded with
`MacBook Air Microphone` even though `External Microphone` was available. Its saved
`avfoundation:0` ID identified an enumeration position, not a persistent microphone
identity; the logs cannot establish whether that position had changed.

## Selection policy

- Automatic mode resolves connected inputs when recording starts. Legacy saved
  device IDs also use automatic selection, so a reused number cannot select the
  internal microphone.
- A single identifiable external input (USB, External Microphone, or AudioMoth) is
  selected automatically. Unknown input names and multiple candidates require a
  choice in NFC Tools Settings.
- Known built-in, headset, camera, default, and loopback inputs are excluded. No
  suitable external input means recording does not start.
- Explicit choices are saved by exact device name. Missing or duplicate names
  stop selection rather than substituting another input. The user can return to
  automatic mode in Settings.
- Recording, readiness, diagnostics, the preview meter, and CLI checks share this
  policy. The sounddevice backend also requires an unambiguous exact name match;
  it never falls back to the OS default or first input.
- Settings show the current resolved input; it is checked again at recording
  startup. Existing recording diagnostics log the actual opened device.

Classification is conservative and name-based. It cannot guarantee physical
transport or sensitivity for every device model. Unknown recording devices can
be explicitly selected, while devices with identical names must be disambiguated
by disconnecting the other device. A full hardware identity system is outside
this fix.

Regression coverage includes the reported device combination, reordered device
indices, missing and ambiguous inputs, and backend fallback prevention.
