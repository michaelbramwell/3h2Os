from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
import logging

from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.services.garmin import GarminService
from app.services.sync import SyncService
from app.services.feature_flags import FeatureFlagService
from app.schemas import (
    GarminLogin,
    GarminToken,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Garmin"])

_GARMIN_DISABLED_DETAIL = "Garmin integration is not currently available."


def get_sync_service(session: Session = Depends(get_session)) -> SyncService:
    return SyncService(session)


def get_feature_flag_service(
    session: Session = Depends(get_session),
) -> FeatureFlagService:
    return FeatureFlagService(session)


@router.post("/garmin/token", response_model=GarminToken)
def get_garmin_token(
    creds: GarminLogin,
    user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Authenticate with Garmin Connect using credentials and return an OAuth token archive.
    The credentials are not stored on the server.
    """
    if not flag_service.is_enabled("isGarminEnabled", user):
        raise HTTPException(status_code=403, detail=_GARMIN_DISABLED_DETAIL)
    try:
        # Use static method, no session needed for login generation
        token_str = GarminService.generate_tokens(creds.email, creds.password)
        return {"token": token_str}
    except ValueError as e:
        logger.warning(f"Garmin auth failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Garmin auth internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Service Error")


@router.post("/garmin/token/refresh", response_model=GarminToken)
def refresh_garmin_token(
    request: Request,
    user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Refresh an existing Garmin OAuth token archive without SSO.

    Exchanges the stored OAuth1 token for a fresh OAuth2 token using garth's
    token exchange — no Garmin credentials are required. Returns an updated
    token archive to replace the one stored in the browser.

    Returns 401 if the underlying OAuth1 token has also expired, in which case
    the user must reconnect with their credentials.
    """
    if not flag_service.is_enabled("isGarminEnabled", user):
        raise HTTPException(status_code=403, detail=_GARMIN_DISABLED_DETAIL)
    token = request.headers.get("X-Garmin-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Garmin Token in headers")
    try:
        new_token_str = GarminService.refresh_tokens(token)
        return {"token": new_token_str}
    except ValueError as e:
        logger.warning(f"Garmin token refresh failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Garmin token refresh internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Service Error")


@router.post("/integrations/garmin/sync")
async def sync_garmin_activities(
    request: Request,
    days: int = 7,
    sync_service: SyncService = Depends(get_sync_service),
    user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Syncs activities from Garmin Connect for the specified number of past days.
    Requires X-Garmin-Token header.
    """
    if not flag_service.is_enabled("isGarminEnabled", user):
        raise HTTPException(status_code=403, detail=_GARMIN_DISABLED_DETAIL)
    token = request.headers.get("X-Garmin-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Garmin Token in headers")

    try:
        count = sync_service.sync_garmin(user, token, days)
        return {
            "status": "success",
            "count": count,
            "message": f"Synced {count} activities.",
        }
    except ValueError as e:
        # e.g., token invalid
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/integrations/sync")
async def sync_both_activities(
    request: Request,
    days: int = 7,
    sync_service: SyncService = Depends(get_sync_service),
    user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Sync from both Strava (primary) and Garmin (enrichment) when both are connected.
    Requires X-Garmin-Token header. Strava runs first, then Garmin patches
    Garmin-only fields (aerobic_te, anaerobic_te, training_load) onto matched records.
    """
    if not flag_service.is_enabled("isGarminEnabled", user):
        raise HTTPException(status_code=403, detail=_GARMIN_DISABLED_DETAIL)
    token = request.headers.get("X-Garmin-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Garmin Token in headers")

    try:
        counts = sync_service.sync_both(user, token, days)
        return {
            "status": "success",
            "strava_synced": counts["strava"],
            "garmin_enriched": counts["garmin"],
            "days": days,
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Combined sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
