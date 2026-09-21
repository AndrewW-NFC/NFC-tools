# Shared overnight precipitation contract

Both NFC Tools `precipitation.py` and the acoustic app `precipitation.js` implement
`overnight-precipitation-v1`. The fixture cases in both repositories must stay identical.

- Window: evening date at 18:00 through the next date at 06:00, in the saved site's IANA timezone. This is independent of recording segments and astronomical twilight.
- Provider: Open-Meteo Historical Weather API (`https://archive-api.open-meteo.com/v1/archive`), pinned `models=ecmwf_ifs`, `hourly=precipitation`, `precipitation_unit=mm`, `cell_selection=land`, UTC Unix timestamps. No silent source fallback; this source begins in 2017.
- Variable: total precipitation water equivalent, including snow. These are modeled estimates, not measured rainfall or NWS station observations.
- Each timestamp ends the preceding one-hour accumulation. Include interval ends strictly after the window start and at or before its end.
- Count each UTC interval once. Identical duplicate values count once; conflicting duplicates make that interval unavailable.
- Null, absent, negative, nonnumeric, and wrong-unit values are unavailable, never dry weather. An unfinished night cannot have a complete total. Publish a total only when every expected interval is valid; keep any available subtotal explicitly separate.
- Use UTC elapsed time, including 11/13-hour US daylight-saving nights. For zones whose local window does not align with the source's hourly grid, unmatched intervals remain unavailable rather than being silently prorated.
- Sum unrounded millimeters, then convert using 25.4 mm/in. JSON totals use six decimal places; UI inches use three.
- Record requested coordinates, returned grid coordinates/elevation, timezone, accumulation bounds, model, retrieval time, interval data and coverage. Provider revisions may change a later retrieval; complete means coverage-complete, not a final gauge observation.

## NFC Tools

Original `environmental_conditions.csv` and TXT remain recording-start snapshots.
New rows carry the selected weather interval and provisional status. Do not sum
snapshot rows: restarts can repeat an hour and later fetches can revise its value.

Recording stop attempts a separate `logs/overnight_precipitation.json` report.
Opening Night Summary fetches a missing/incomplete summary once per page visit.
Use **Refresh overnight precipitation** to reconcile after 06:00 or after source
updates. Fetch failures retain the previous saved report. The saved recording
coordinates/timezone are used; mixed locations are rejected. Imports can be
reconciled from Night Summary too.

Headless usage: `nfc precipitation /path/to/recordings/2026-09-20`.

## Acoustic app

Completed historical night cards, TXT/JSON, and historical CSV exports include the
same separate overnight summary. CSV summary columns begin `overnight_`; when
hourly rows are requested, `overnight_precipitation_hour` rows provide its inputs.
The existing `hourly` rows remain the twilight scoring inputs and must not be
summed together with the new overnight interval rows. Scoring subtotals are
labeled separately because their source selection and interval window differ.

Missing scoring precipitation now remains missing. It receives a neutral score
contribution with a provisional warning rather than a dry-weather benefit.

Run `node --test tests/precipitation.test.cjs` in the acoustic project and
`python -m pytest tests/test_precipitation.py` in NFC Tools.
