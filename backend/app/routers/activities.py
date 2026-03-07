from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
import logging

from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.services.activities import ActivityService
from app.services.plans import PlanService
from app.services.context import ContextService
from app.schemas import ActivitySchema, ContextSchema

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Activities"])


def get_activity_service(session: Session = Depends(get_session)) -> ActivityService:
    return ActivityService(session)


def get_plan_service(session: Session = Depends(get_session)) -> PlanService:
    return PlanService(session)


def get_context_service(session: Session = Depends(get_session)) -> ContextService:
    return ContextService(session)


@router.post("/actuals")
async def save_actuals(
    activities: List[ActivitySchema],
    service: ActivityService = Depends(get_activity_service),
    user: User = Depends(get_current_user),
):
    """
    Bulk save/update actual activities.
    """
    try:
        count = service.save_activities(activities, user=user)
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actuals.json", response_model=List[ActivitySchema])
async def get_actuals(
    service: ActivityService = Depends(get_activity_service),
    plan_service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Get the actual activities from the database, filtered by the active plan type.
    """
    # Use service method to determine filter types based on active plan
    filter_types = plan_service.get_active_plan_activity_types(user)
    return service.get_activities(user=user, filter_types=filter_types)


@router.get("/context.json", response_model=ContextSchema)
async def get_context(
    service: ContextService = Depends(get_context_service),
    user: User = Depends(get_current_user),
):
    """
    Get the context data
    """
    return service.get_context(user=user)


@router.get("/context/markdown")
async def get_context_markdown():
    """
    Deprecated: Context is now database-driven.
    """
    return {"content": ""}
