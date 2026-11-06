# BirdNET 3 upgrade

The normal `nfc-tools` app now uses acoustic model 3.0 (developer preview 3.1),
Analyzer commit `032dcaca6afb2a3438965f80d5e01de0fb2036b4`, and `birdnet==1.4.0`.
This integrates the development work without changing production settings,
port 8765, recording schedules, selected analyzers, or output location.
The development launcher remains isolated on port 8766 with its trial restrictions.

## Existing recordings and settings

The installer creates `analyzers/birdnet3` in the app data directory and leaves
`analyzers/birdnet` untouched. The first analysis downloads models into the
profile's `birdnet-models` folder. Allow extra disk space and setup time.

Do not combine BirdNET 2.4 and 3 analyses in one output folder. Finish old imports
with the previous app, or start a new import in a fresh folder. The new app
refuses to resume BirdNET jobs/checkpoints from a different or unidentified
version, and protects older results found in the same night. Old results remain
available for review. Version identity is recorded in new jobs and checkpoints.

Confidence scores are not equivalent between versions. The normal threshold
and 0.25 finch/owl boosts are retained, but need evaluation with manually reviewed
night recordings. Taxonomy changes can change labels and eBird matches; review
any unresolved names before uploading. The integration preserves the latest
robin-call wingbeat filtering and readable non-avian clip filenames.

## Returning to the previous version on this Mac

The previous code is retained at `~/Desktop/nfc-tools-previous`, at commit
`c270c57`. Close the new app first, then run `nfc-tools-previous` in Terminal.
It uses the retained BirdNET 2.4 installation and the normal settings.
Use separate output folders for new work with either version: the previous
app does not know how to protect BirdNET 3 results from version mixing.
To return to BirdNET 3, close the previous app and run `nfc-tools`.

A copy of the pre-upgrade configuration and launcher scripts is kept in:

```text
~/Library/Application Support/nfc-tools/backups/pre-birdnet3-2026-11-06/
```

No settings restore is normally necessary. Restoring the saved `config.yaml`
would also discard any settings changes made since this upgrade.

## Validation

See `birdnet-3-validation-2026-11-06.md` for the actual checks and limitations.
The automated scheduling tests simulate recording devices and clock events;
they do not replace a full overnight test with the intended microphone.
A short successful inference check establishes software compatibility, not
flight-call identification accuracy.

Upstream references:
- https://birdnet-team.github.io/BirdNET-Analyzer/dev/breaking-changes.html
- https://github.com/birdnet-team/birdnet-V3.0-dev
