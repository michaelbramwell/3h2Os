from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session
import os
import logging
from typing import Optional

from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.routers.events import push_event
from app.services.strava import StravaService
from app.services.sync import SyncService
from app.core.auth import allow_anonymous
from app.schemas import (
    StravaAuthUrlResponse,
    StravaStatusResponse,
    StravaExchangeRequest,
    StravaExchangeResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Strava"])

# Webhook path includes a secret token so the URL is unguessable.
# When registering the subscription with Strava, use the full URL including this segment.
_WEBHOOK_SECRET = os.environ.get("STRAVA_WEBHOOK_SECRET", "")
_WEBHOOK_PATH = (
    f"/strava/webhook/{_WEBHOOK_SECRET}" if _WEBHOOK_SECRET else "/strava/webhook"
)


def get_strava_service(session: Session = Depends(get_session)) -> StravaService:
    return StravaService(session)


def get_sync_service(session: Session = Depends(get_session)) -> SyncService:
    return SyncService(session)


@router.get("/strava/auth-url", response_model=StravaAuthUrlResponse)
async def strava_auth_url(
    user: User = Depends(get_current_user),
    strava: StravaService = Depends(get_strava_service),
):
    """Return the Strava OAuth authorization URL for the current user."""
    return StravaAuthUrlResponse(url=strava.get_auth_url(user.id))


@router.post("/strava/exchange", response_model=StravaExchangeResponse)
async def strava_exchange(
    body: StravaExchangeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Exchange a Strava authorization code for tokens.
    Called by the frontend after Strava redirects back with ?code=&state=.
    """
    from app.services.strava import verify_state_token

    try:
        verify_state_token(body.state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid state token: {e}")

    try:
        strava = StravaService(session)
        token_data = strava.exchange_code(body.code)
        strava.save_token(user.id, token_data)

        try:
            strava.merge_athlete_profile(user.id, token_data["access_token"])
        except Exception as e:
            logger.warning(f"Strava athlete profile merge failed (non-fatal): {e}")

        return StravaExchangeResponse(ok=True)
    except Exception as e:
        logger.error(f"Strava exchange error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Strava token exchange failed")


@router.get("/strava/status", response_model=StravaStatusResponse)
async def strava_status(
    user: User = Depends(get_current_user),
    strava: StravaService = Depends(get_strava_service),
):
    """Return whether the current user has Strava connected."""
    token = strava.get_token(user.id)
    if not token:
        return StravaStatusResponse(connected=False)
    return StravaStatusResponse(
        connected=True,
        athlete_id=token.athlete_id,
        scope=token.scope,
    )


@router.delete("/strava/disconnect")
async def strava_disconnect(
    user: User = Depends(get_current_user),
    strava: StravaService = Depends(get_strava_service),
):
    """Disconnect Strava by deleting the stored token."""
    strava.disconnect(user.id)
    return {"status": "disconnected"}


@router.post("/integrations/strava/sync")
async def sync_strava_activities(
    days: int = 7,
    sync_service: SyncService = Depends(get_sync_service),
    user: User = Depends(get_current_user),
):
    """
    Sync Strava activities for the past N days.
    """
    try:
        saved_count = sync_service.sync_strava(user, days)
        return {"synced": saved_count, "days": days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Strava sync error for user {user.username}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Strava API error: {str(e)}")


@router.get(_WEBHOOK_PATH)
@allow_anonymous
async def strava_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Strava webhook subscription verification (GET handshake).
    """
    # Use os.environ.get instead of missing param
    expected_token = os.environ.get("STRAVA_WEBHOOK_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_challenge and hub_verify_token == expected_token:
        return JSONResponse({"hub.challenge": hub_challenge})
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post(_WEBHOOK_PATH)
@allow_anonymous
async def strava_webhook_event(
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Strava webhook event receiver (POST).
    Handles:
    - athlete deauthorization: deletes the stored token so we hold no data for revoked users.
    - activity create/update: triggers a short sync for the affected athlete.
    """
    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    strava = StravaService(session)
    synced_user_id = strava.handle_webhook_event(event)

    if synced_user_id is not None:
        await push_event(synced_user_id, "activities_updated", {})

    # All event types — acknowledge
    return {"status": "ok"}
