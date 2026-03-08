from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import logging
import os as _os
from typing import List

from app.core.database import User, get_session
from app.core.auth import require_role
from app.routers.deps import get_current_user
from app.services.feature_flags import FeatureFlagService
from app.schemas import (
    FeatureFlagSchema,
    FeatureFlagUpdate,
    UserFlagsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Flags"])

_ADMIN_ROLE = _os.getenv("ADMIN_ROLE", "app_admin")

def get_feature_flag_service(
    session: Session = Depends(get_session),
) -> FeatureFlagService:
    return FeatureFlagService(session)

@router.get("/flags", response_model=UserFlagsResponse)
async def get_flags_for_current_user(
    user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Return all feature flags resolved to True/False for the current user.
    Example response: {"flags": {"isSwimmingEnabled": false}}
    """
    try:
        flags = service.get_flags_for_user(user)
        return UserFlagsResponse(flags=flags)
    except Exception as e:
        logger.error(f"Error getting feature flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/flags", response_model=List[FeatureFlagSchema])
async def admin_list_flags(
    _: None = Depends(require_role(_ADMIN_ROLE)),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Admin: list all feature flags with their raw enabled_for configuration.
    Requires the '{ADMIN_ROLE}' Keycloak realm role (default: 'app_admin').
    """
    try:
        import json

        flags = service.list_flags()
        return [
            FeatureFlagSchema(
                id=f.id,
                name=f.name,
                enabled_for=json.loads(f.enabled_for_json or "[]"),
                description=f.description,
            )
            for f in flags
        ]
    except Exception as e:
        logger.error(f"Error listing flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/flags/{flag_name}", response_model=FeatureFlagSchema)
async def admin_set_flag(
    flag_name: str,
    payload: FeatureFlagUpdate,
    _: None = Depends(require_role(_ADMIN_ROLE)),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Admin: create or update a feature flag.
    Pass enabled_for=["*"] to enable for all, [] to disable, or a list of user types.
    Requires the '{ADMIN_ROLE}' Keycloak realm role (default: 'app_admin').
    """
    try:
        import json

        flag = service.set_flag(flag_name, payload.enabled_for, payload.description)
        return FeatureFlagSchema(
            id=flag.id,
            name=flag.name,
            enabled_for=json.loads(flag.enabled_for_json or "[]"),
            description=flag.description,
        )
    except Exception as e:
        logger.error(f"Error setting flag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
