"""Timezone UI helpers.

Timezone is no longer user-facing. The app stores an IANA timezone internally
for timestamps and weather logs, normally from the computer/geocoder defaults.
"""

from __future__ import annotations


def timezone_select_groups(selected_timezone: str | None = None) -> list[dict]:
    """Compatibility stub for older routes/templates."""
    return []
