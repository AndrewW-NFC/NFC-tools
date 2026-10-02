# eBird reviewer rarity filters

## Testing status

Testing is underway for adding regional rarity reminders to species comments in
eBird bulk-upload CSVs. This feature is not ready for broader distribution.

The current importer was built against one reviewer-provided example from
Middlesex County, Massachusetts. We have not established that other reviewers
provide exports in the same format. These requirements describe the NFC Tools
importer, not a universal eBird reviewer-export specification. If another reviewer
provides a different structure, inspect that file and adapt the importer before
claiming support for it.

## Supported input structure

- UTF-8, comma-separated CSV with no header row, no larger than 2 MiB.
- First column: exact eBird common name. Names must be unique within the file.
- Remaining columns: alternating date and threshold pairs. Each row must have at
  least one pair; different taxa may have different numbers of pairs.
- Each row begins with `Jan 1`. Subsequent dates must be strictly increasing,
  without duplicates.
- Dates use English three-letter month names and day numbers, such as `Sep 30`.
  Years are omitted because thresholds repeat annually.
- Thresholds are nonnegative whole numbers. Blank or fractional counts are not
  supported.
- Quoted names, a UTF-8 byte-order mark, and Windows line endings are supported.
  Blank rows are ignored, and surrounding cell whitespace is stripped.
- February 29 change points are not supported. Recordings made on February 29
  are evaluated normally using the threshold already in effect.

Synthetic example (not actual reviewer data):

```csv
Example bird,Jan 1,0,May 1,20,Oct 1,0
Another example bird,Jan 1,0
```

For the first row, zero-threshold periods are January 1–April 30 and October
1–December 31. The second row has a zero threshold all year.

## Interpretation and matching

Each threshold takes effect on its listed date and continues through the day
before the next date; the last threshold continues through December 31.
Positive thresholds must remain in the imported data because they end zero
periods, even though NFC Tools does not generate high-count warnings.

Only a zero threshold adds this exact sentence to existing species comments:

> Flagged rare for species and/or date. Provide recording or description of the call.

Matching uses each recording's local start date, also written into its eBird
checklist. A September 30 recording at 11:35 p.m. uses September 30's threshold;
the following October 1 recording at midnight uses October 1's threshold, even
when both recordings share an overnight folder. Imported recordings use their
corrected local dates.

Names absent from the filter are **not evaluated**. Matching is exact, with no
fuzzy matching or automatic taxonomy aliases. A species-specific rule is not
applied to a broader identification with a different name.

## Local handling and limitations

Import the CSV in Settings, provide its region, confirm coverage for the recording
and eBird location, and enable reminders. Parsed data is copied into the local
configuration, so moving the original file does not break the filter. Invalid
uploads are rejected with an error and preserve the previously saved filter.

The filter is optional and off by default. Changing location requires checking
coverage again. Review CSVs record the evaluation, applicable date interval,
region, source filename, import timestamp, and source checksum. These results
reflect the imported data and may differ from eBird's current filters.

Users can add recordings or call descriptions in eBird after upload; there is no
pre-upload documentation requirement in NFC Tools. Reviewer data is not bundled
with the application or this reference. Keep actual reviewer files and local
configuration/import snapshots out of the repository; use synthetic examples
for public documentation and tests.
