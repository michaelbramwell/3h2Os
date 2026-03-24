from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session

from app.core.auth import allow_anonymous
from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.schemas import ActivitySchema
from app.services.share import ShareService

router = APIRouter(tags=["Share"])


def get_share_service(session: Session = Depends(get_session)) -> ShareService:
    return ShareService(session)


@router.get("/share/{token}", response_model=ActivitySchema)
@allow_anonymous
async def get_shared_activity(
    token: str,
    service: ShareService = Depends(get_share_service),
):
    """
    Public endpoint — no auth required.
    Returns the activity associated with the given share token.
    """
    activity = service.get_activity_by_token(token)
    if activity is None:
        raise HTTPException(status_code=404, detail="Share not found")
    return activity


@router.post("/activities/{activity_id}/share")
async def create_share(
    activity_id: int,
    request: Request,
    service: ShareService = Depends(get_share_service),
    user: User = Depends(get_current_user),
):
    """
    Authenticated endpoint.
    Creates (or returns existing) share token for the given activity.
    The share URL is derived from the incoming request's base URL so it works
    in local dev and production without any hardcoded domain.
    """
    try:
        share = service.create_share(activity_id=activity_id, user_id=user.id)
    except ValueError:
        raise HTTPException(
            status_code=403, detail="Activity not found or access denied"
        )

    base_url = str(request.base_url).rstrip("/")
    return {
        "token": share.token,
        "url": f"{base_url}/share/{share.token}",
    }
