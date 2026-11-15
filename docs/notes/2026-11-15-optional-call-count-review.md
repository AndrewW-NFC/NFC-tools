# Automatic estimated counts

Approved November 15, 2026 as a fix for detected species disappearing from
eBird exports when overlapping model windows leave call counts uncertain.

The user rejected a separate audio-review step for counts and approved automatic
estimates. Each connected group of overlapping or touching windows for one
recording/taxon estimates one event; positive gaps separate events. Comments
start with `NFC <count> (estimated)` at night and `Unique detections <count>
(estimated)` outside that window, followed by raw model totals. No pending-review
or count-review-required text appears in species comments. Abundance defaults
to `X`, and count uncertainty does not block export or readiness.

Optional existing count overrides remain supported; zero totals omit the species.
Taxonomy eligibility is unchanged. Grouping can undercount multiple calls within
connected windows and does not establish bird abundance or validate species
identification. Do not restore mandatory count review as an export prerequisite.
