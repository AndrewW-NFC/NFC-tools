# Species-level comments: detection-model breakdown

Recorded November 12, 2026. The user explicitly authorized implementing and
pushing this enhancement now as an exception to the project hold.

Species-level export comments include both models in the total and show each
model's contribution, including zero counts:

```text
NFC 14 | Nighthawk detections 10 | BirdNET detections 4
```

Outside the NFC period, the total retains the `Flight call` label. Nighthawk
broad-category details and rarity annotations remain available. Wingbeats remain
review-only and do not contribute to the NFC total.

Totals count model detections, not deduplicated unique calls. A call detected by
both models contributes to both model counts and requires manual review.
