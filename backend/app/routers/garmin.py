from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session
import logging

from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.services.garmin import GarminService
from app.services.sync import SyncService
from app.schemas import (
    GarminLogin,
    GarminToken,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Garmin"])


def get_sync_service(session: Session = Depends(get_session)) -> SyncService:
    return SyncService(session)


@router.post("/garmin/token", response_model=GarminToken)
def get_garmin_token(creds: GarminLogin):
    """
    Authenticate with Garmin Connect using credentials and return an OAuth token archive.
    The credentials are not stored on the server.
    """
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


@router.post("/integrations/garmin/sync")
async def sync_garmin_activities(
    request: Request,
    days: int = 7,
    sync_service: SyncService = Depends(get_sync_service),
    user: User = Depends(get_current_user),
):
    """
    Syncs activities from Garmin Connect for the specified number of past days.
    Requires X-Garmin-Token header.
    """
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
