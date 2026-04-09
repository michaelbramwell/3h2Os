"""
profile_sync.py — shared helpers for per-source, per-field sync preferences.

The preference model is intentionally simple:

  • Each field is "owned" by at most ONE source at any given time.
  • If a source toggle is on, the field is read-only in the manual-edit UI.
  • If BOTH toggles are off the field is editable manually and sync won't touch it.
  • Defaults (when prefs are absent) are defined in DEFAULTS below.
  • For shared fields (weight), Strava takes priority by default.

Supported sources:   "garmin" | "strava"
Supported fields per source:
    garmin: weight, height, resting_hr, vo2max, lactate_threshold
    strava: weight, ftp, hr_zones

Fields that only one source provides are straightforward on/off.
Fields shared between sources (weight) use mutual-exclusion logic.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

# Which fields each source can write, and their default enabled state.
# For shared fields (weight) the default gives Strava priority.
DEFAULTS: dict[str, dict[str, bool]] = {
    "garmin": {
        # weight defaults False because Strava is on by default for weight
        "weight": False,
        "height": True,
        "resting_hr": True,
        "vo2max": True,
        "lactate_threshold": True,
    },
    "strava": {
        "weight": True,
        "ftp": True,
        "hr_zones": True,
    },
}

# Fields that are shared between sources — only one may be active at a time.
# The first source listed wins the tiebreaker if both are somehow True.
SHARED_FIELDS: dict[str, list[str]] = {
    "weight": ["strava", "garmin"],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_prefs(profile_sync_prefs_json: str | None) -> dict[str, dict[str, bool]]:
    """
    Parse the stored JSON prefs, falling back to DEFAULTS for any missing key.
    Returns a fully-populated prefs dict.
    """
    stored: dict[str, Any] = {}
    if profile_sync_prefs_json:
        try:
            stored = json.loads(profile_sync_prefs_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Corrupt profile_sync_prefs_json; using defaults.")

    result: dict[str, dict[str, bool]] = {}
    for source, field_defaults in DEFAULTS.items():
        result[source] = {}
        for field, default_val in field_defaults.items():
            result[source][field] = stored.get(source, {}).get(field, default_val)

    return result


def dump_prefs(prefs: dict[str, dict[str, bool]]) -> str:
    """Serialise prefs to a compact JSON string for storage."""
    return json.dumps(prefs, separators=(",", ":"))


def can_write(prefs: dict[str, dict[str, bool]], source: str, field: str) -> bool:
    """
    Return True if *source* is allowed to write *field*.

    For shared fields this also checks that no other source has claimed the field
    (defensive; the UI should have already enforced mutual exclusion).
    """
    source_prefs = prefs.get(source, {})
    if not source_prefs.get(field, False):
        return False

    # Mutual-exclusion guard for shared fields
    if field in SHARED_FIELDS:
        for other_source in SHARED_FIELDS[field]:
            if other_source == source:
                continue
            if prefs.get(other_source, {}).get(field, False):
                # Both are marked True — this shouldn't happen after UI enforcement,
                # but if it does, the source that is listed first in SHARED_FIELDS wins.
                winning_source = SHARED_FIELDS[field][0]
                return source == winning_source

    return True


def apply_toggle(
    prefs: dict[str, dict[str, bool]],
    source: str,
    field: str,
    enabled: bool,
) -> dict[str, dict[str, bool]]:
    """
    Set *source*/*field* to *enabled*, enforcing mutual exclusion on shared fields.

    When enabling a shared field on one source, the same field is automatically
    disabled on all other sources.
    """
    import copy

    result = copy.deepcopy(prefs)

    if source not in result:
        result[source] = {}
    result[source][field] = enabled

    if enabled and field in SHARED_FIELDS:
        for other_source in SHARED_FIELDS[field]:
            if other_source != source:
                if other_source not in result:
                    result[other_source] = {}
                result[other_source][field] = False

    return result
