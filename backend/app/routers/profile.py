"""
profile.py — API endpoints for the global runner profile and sync preferences.

Endpoints:
  GET  /api/profile              → ProfileResponse
  PATCH /api/profile             → ProfileResponse  (manual field edits)
  PATCH /api/profile/sync-prefs  → ProfileSyncPrefs (toggle a source/field)
  POST  /api/profile/sync-now    → {"ok": true, "synced_at": "..."}
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.core.database import RunnerProfile, User, get_session
from app.core.profile_sync import (
    DEFAULTS,
    apply_toggle,
    can_write,
    dump_prefs,
    load_prefs,
)
from app.routers.deps import get_current_user
from app.schemas import (
    GarminSyncPrefs,
    ProfilePatch,
    ProfileResponse,
    ProfileSyncPrefs,
    StravaSyncPrefs,
    SyncPrefsUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Profile"])

# Fields that each source "owns" (maps to profile_sync.DEFAULTS keys)
_GARMIN_FIELDS = set(DEFAULTS.get("garmin", {}).keys())
_STRAVA_FIELDS = set(DEFAULTS.get("strava", {}).keys())

# Mapping from pref field name → RunnerProfile attribute name
_FIELD_TO_ATTR: dict[str, str] = {
    "weight": "weight_kg",
    "height": "height_cm",
    "resting_hr": "resting_hr",
    "vo2max": "vo2max",
    "lactate_threshold": "lactate_threshold_hr",  # covers both hr + pace columns
    "ftp": "ftp",
    # hr_zones maps to training_zones_json; not a simple scalar — excluded from manual edit
}


def _get_or_404(session: Session, user: User) -> RunnerProfile:
    profile = session.exec(
        select(RunnerProfile).where(RunnerProfile.user_id == user.id)
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def _build_response(profile: RunnerProfile) -> ProfileResponse:
    prefs_raw = load_prefs(profile.profile_sync_prefs_json)
    sync_prefs = ProfileSyncPrefs(
        garmin=GarminSyncPrefs(**prefs_raw.get("garmin", {})),
        strava=StravaSyncPrefs(**prefs_raw.get("strava", {})),
    )
    return ProfileResponse(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        birthday=profile.birthday,
        weight_kg=profile.weight_kg,
        ftp=profile.ftp,
        resting_hr=profile.resting_hr,
        vo2max=profile.vo2max,
        lactate_threshold_hr=profile.lactate_threshold_hr,
        lactate_threshold_pace=profile.lactate_threshold_pace,
        experience_level=profile.experience_level,
        weekly_availability=profile.weekly_availability,
        sync_prefs=sync_prefs,
        profile_last_synced_at=profile.profile_last_synced_at,
    )


# ---------------------------------------------------------------------------
# GET /api/profile
# ---------------------------------------------------------------------------


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    """Return the current user's runner profile with sync preferences."""
    profile = _get_or_404(session, user)
    return _build_response(profile)


# ---------------------------------------------------------------------------
# PATCH /api/profile
# ---------------------------------------------------------------------------


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(
    body: ProfilePatch,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProfileResponse:
    """
    Manually update profile fields.
    Any field currently owned by a source (source toggle is ON) is silently
    skipped — the source owns it and manual edits are not permitted.
    """
    profile = _get_or_404(session, user)
    prefs = load_prefs(profile.profile_sync_prefs_json)

    # Determine which fields are source-owned (any source has it enabled)
    def _is_source_owned(pref_field: str) -> bool:
        for source in ("garmin", "strava"):
            if can_write(prefs, source, pref_field):
                return True
        return False

    # Scalar field map: ProfilePatch attr → (pref field name or None, profile attr)
    scalar_map: list[tuple[str, str | None, str]] = [
        ("age", None, "age"),  # bio — always manually editable
        ("gender", None, "gender"),  # bio — always manually editable
        ("height_cm", "height", "height_cm"),
        ("weight_kg", "weight", "weight_kg"),
        ("ftp", "ftp", "ftp"),
        ("resting_hr", "resting_hr", "resting_hr"),
        ("vo2max", "vo2max", "vo2max"),
        ("lactate_threshold_hr", "lactate_threshold", "lactate_threshold_hr"),
        ("lactate_threshold_pace", "lactate_threshold", "lactate_threshold_pace"),
        ("experience_level", None, "experience_level"),  # no source owns this
        ("weekly_availability", None, "weekly_availability"),  # no source owns this
    ]

    changed = False
    for patch_attr, pref_field, profile_attr in scalar_map:
        value = getattr(body, patch_attr, None)
        if value is None:
            continue
        # Skip if a source owns this field
        if pref_field and _is_source_owned(pref_field):
            logger.debug(
                f"Skipping manual edit of '{patch_attr}' — owned by a sync source"
            )
            continue
        setattr(profile, profile_attr, value)
        changed = True

    if changed:
        session.add(profile)
        session.commit()
        session.refresh(profile)

    return _build_response(profile)


# ---------------------------------------------------------------------------
# PATCH /api/profile/sync-prefs
# ---------------------------------------------------------------------------


@router.patch("/profile/sync-prefs", response_model=ProfileSyncPrefs)
def patch_sync_prefs(
    body: SyncPrefsUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ProfileSyncPrefs:
    """
    Toggle a single source/field sync preference.
    Enforces mutual exclusion for shared fields (e.g. weight).
    Returns the updated sync prefs.
    """
    profile = _get_or_404(session, user)

    # Validate field is known for the given source
    known_fields = DEFAULTS.get(body.source, {})
    if body.field not in known_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Field '{body.field}' is not valid for source '{body.source}'",
        )

    prefs = load_prefs(profile.profile_sync_prefs_json)
    prefs = apply_toggle(prefs, body.source, body.field, body.enabled)
    profile.profile_sync_prefs_json = dump_prefs(prefs)
    session.add(profile)
    session.commit()

    return ProfileSyncPrefs(
        garmin=GarminSyncPrefs(**prefs.get("garmin", {})),
        strava=StravaSyncPrefs(**prefs.get("strava", {})),
    )


# ---------------------------------------------------------------------------
# POST /api/profile/sync-now
# ---------------------------------------------------------------------------


@router.post("/profile/sync-now")
def sync_profile_now(
    request: Request,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Trigger an on-demand profile sync from all connected sources.
    Garmin sync requires the X-Garmin-Token header — if absent, it is skipped.
    Strava sync runs if a token is present in the database.
    """
    synced_sources: list[str] = []

    # --- Strava ---
    try:
        from app.core.database import StravaToken
        from app.services.strava import StravaService

        strava_token = session.exec(
            select(StravaToken).where(StravaToken.user_id == user.id)
        ).first()
        if strava_token:
            svc = StravaService(session)
            refreshed = svc.refresh_if_needed(strava_token)
            svc.merge_athlete_profile(user.id, refreshed.access_token)
            synced_sources.append("strava")
    except Exception as e:
        logger.warning(f"sync-now Strava failed for user {user.id}: {e}")

    # --- Garmin ---
    garmin_token = request.headers.get("X-Garmin-Token")
    if garmin_token:
        try:
            from app.services.garmin import GarminService

            garmin_svc = GarminService(session=session, token_b64=garmin_token)
            garmin_svc.fetch_user_profile(user.id)
            synced_sources.append("garmin")
        except Exception as e:
            logger.warning(f"sync-now Garmin failed for user {user.id}: {e}")

    # Refresh training zones from best available source
    try:
        from app.core.zones import refresh_training_zones

        profile_for_zones = _get_or_404(session, user)
        refresh_training_zones(profile_for_zones, session)
    except Exception as e:
        logger.warning(f"sync-now zone refresh failed for user {user.id}: {e}")

    profile = _get_or_404(session, user)
    synced_at = (
        profile.profile_last_synced_at.isoformat()
        if profile.profile_last_synced_at
        else None
    )
    return {
        "ok": True,
        "synced": bool(synced_sources),
        "synced_sources": synced_sources,
        "synced_at": synced_at,
        "message": f"Synced from: {', '.join(synced_sources)}"
        if synced_sources
        else "No sources synced",
    }
