"""Shared eligibility and confidence rules for BirdNET review candidates."""

# Role: Keeps BirdNET analysis filtering and clip selection consistent.
# Dependencies: Standard-library math; callers supply analyzer configuration and labels.
from __future__ import annotations

import math

HIGH_SENSITIVITY_CONFIDENCE = 0.25
# Scientific names are matched against the installed model, not translated labels.
WINTER_FINCHES = {
    "Spinus pinus": "Pine Siskin",
    "Coccothraustes vespertinus": "Evening Grosbeak",
    "Hesperiphona vespertina": "Evening Grosbeak",
    "Pinicola enucleator": "Pine Grosbeak",
    "Acanthis flammea": "Common Redpoll",
    "Acanthis hornemanni": "Hoary Redpoll",
    "Acanthis cabaret": "Lesser Redpoll",
    "Loxia curvirostra": "Red Crossbill",
    "Loxia leucoptera": "White-winged Crossbill",
}
# Explicit US/Canada owl set, including southwestern species. No global name matching.
OWLS = {
    "Tyto alba": "Barn Owl", "Tyto furcata": "American Barn Owl",
    "Psiloscops flammeolus": "Flammulated Owl",
    "Megascops asio": "Eastern Screech-Owl",
    "Megascops kennicottii": "Western Screech-Owl",
    "Megascops trichopsis": "Whiskered Screech-Owl",
    "Bubo virginianus": "Great Horned Owl", "Bubo scandiacus": "Snowy Owl",
    "Surnia ulula": "Northern Hawk Owl", "Glaucidium gnoma": "Northern Pygmy-Owl",
    "Glaucidium brasilianum": "Ferruginous Pygmy-Owl",
    "Micrathene whitneyi": "Elf Owl", "Athene cunicularia": "Burrowing Owl",
    "Strix occidentalis": "Spotted Owl", "Strix varia": "Barred Owl",
    "Strix nebulosa": "Great Gray Owl", "Asio otus": "Long-eared Owl",
    "Asio flammeus": "Short-eared Owl", "Aegolius funereus": "Boreal Owl",
    "Aegolius acadicus": "Northern Saw-whet Owl",
}


def enabled_species(analyzers) -> dict[str, str]:
    species = {}
    if getattr(analyzers, "birdnet_winter_finch_sensitivity", False):
        species.update(WINTER_FINCHES)
    if getattr(analyzers, "birdnet_owl_sensitivity", False):
        species.update(OWLS)
    return species


def minimum_confidence(analyzers, scientific: str = "", common: str = "") -> float:
    general = float(getattr(analyzers, "birdnet_min_conf", 0.5))
    species = enabled_species(analyzers)
    # Common-name fallback supports older output tables without scientific names.
    matches = scientific.strip() in species or (not scientific.strip() and common.strip() in species.values())
    if not scientific.strip() and common.strip() == "Redpoll" and getattr(analyzers, "birdnet_winter_finch_sensitivity", False):
        matches = True
    return min(general, HIGH_SENSITIVITY_CONFIDENCE) if matches else general


def keep_detection(row: dict, analyzers) -> bool:
    fields = {key.strip().lower(): value for key, value in row.items() if key}
    try:
        confidence = float(fields.get("confidence", ""))
    except (ValueError, TypeError):
        return False
    return math.isfinite(confidence) and confidence >= minimum_confidence(
        analyzers, fields.get("scientific name", "") or "", fields.get("common name", "") or ""
    )
