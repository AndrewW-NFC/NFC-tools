# Settings, Readiness Check, and main-page copy cleanup

Requested November 18, 2026. Recorded as a proposal under the project hold
through January 10, 2027. The user subsequently explicitly authorized immediate
implementation of these follow-up changes:

- Rename the dashboard option to “Extend into morning flight” and remove its
  duplicate timing line.
- Remove the Settings introductory save-information paragraph and global status
  box, retaining section-level save feedback and retry on failure.
- Move Recording schedule immediately below Default location.

Those changes are implemented. Other proposals below remain deferred.

## Settings page

- Remove the entire block containing “Changes save automatically. Wait for
  ‘Saved’ before leaving. Recording input and format changes apply to the next
  recording; existing recordings and results are unchanged.” and “Settings are
  up to date.”
  Reconfirmed in a follow-up request with the “Save info.jpg” screenshot,
  showing both the explanatory paragraph and the saved-status box.
- Move the “Recording schedule” block below the “Default location” block.
- Remove every occurrence of “Based on your imported filter; it may differ from
  eBird’s current filters. Names absent from the filter are not evaluated.”
  (The request lists this removal twice.)
- Rename “Save location” to “File save location”.
- Remove “Use the Desktop default, or choose an external drive or another folder.”
- Remove “Times use the recorder site's map location and timezone.”
- Arrange the BirdNET block as three options in this order:
  1. “Include all species expected at any time of year at this location.”
  2. “Boost winter finch sensitivity”
  3. “Boost owl sensitivity”
- Put “BirdNET uses each recording’s date and the recorder site to filter likely
  species.” directly below the year-round option as its helper text, styled like
  the owl helper “Include North American owls even when unexpected for this
  location or season.”
- Remove the full explanatory text beginning “Choose a CSV, enter its region,
  and confirm coverage to import automatically. Reload after ‘Saved’ to preview
  the filter. The data is copied into your local configuration, so the original
  file can be moved. Disable reminders above to keep the saved filter without
  using it.”
- Remove the “Example zero-threshold periods (month-day, inclusive):” section
  and its displayed examples (Black-bellied Whistling-Duck, its Northern form,
  Bar-headed Goose, Snow Goose, and Ross's Goose).

## Readiness Check page

- When input volume is too low, begin the message with the warning, such as
  “Input volume is very low. Check microphone placement and input gain; a quiet
  environment can also cause this warning.” Put any other details after it.
- Remove “Run these checks before an overnight session to confirm the
  microphone, save location, power status, analyzers, and environment logging
  are ready enough for recording.”

## Main NFC Tools page

- Rename “Include morning flight recordings” to “Extend into morning flight”.
- Remove the timing line below that option, for example “NFC counting ends:
  5:02 AM · Recording stops: 8:40 AM”. The counting-window information at the top
  of the page already communicates this timing.
- Remove “Save recordings outside the NFC counting window separately.
  Remembered for automatically scheduled sessions too.”

## Documentation and future validation

Reviewed relevant references in README.md, README_DEV.md, and
README_WINGBEATS.md. Updated README.md and README_DEV.md for the implemented label and section-level
save feedback; README_WINGBEATS.md remains accurate without edits. For the
remaining proposals, reconcile guide descriptions and verify the copy removals,
BirdNET option ordering/helper placement, low-input warning ordering, Settings
block order, and the morning-flight label and timing-line removal. Update guide
references to the morning-flight option's label when the rename is implemented.
