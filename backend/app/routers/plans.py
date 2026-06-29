from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from sqlmodel import Session
from dataclasses import asdict

from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.services.plans import PlanService
from app.core.validation import ValidationWarningError
from app.schemas import (
    PlanCreate,
    PlanUpdateResponse,
    WeekSchema,
    WeekUpdate,
    WorkoutCreate,
    WorkoutUpdate,
)

router = APIRouter(tags=["Plans"])


def get_plan_service(session: Session = Depends(get_session)) -> PlanService:
    return PlanService(session)


class PlanMeta(BaseModel):
    id: int
    title: str
    type: str
    is_active: bool
    created_at: datetime
    wizard_input_json: Optional[str] = None

    model_config = {"from_attributes": True}


@router.post("/plans", response_model=PlanUpdateResponse)
async def create_plan(
    plan_create: PlanCreate,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Create a new plan. It is created as inactive by default.
    """
    try:
        plan_dicts = [w.model_dump() for w in plan_create.weeks]
        new_plan = service.create_or_update_plan(
            plan_dicts,
            user=user,
            title=plan_create.title,
            plan_type=plan_create.type,
            activate=False,
            wizard_input=plan_create.wizard_input,
        )
        return {
            "status": "success",
            "message": "Plan created",
            "id": new_plan.id,
            "title": new_plan.title,
            "type": new_plan.type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans", response_model=List[PlanMeta])
async def get_plans(
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Get all plans for the current user.
    """
    try:
        plans = service.get_plans(user)
        return plans
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}/activate")
async def set_active_plan(
    plan_id: int, service: PlanService = Depends(get_plan_service)
):
    """
    Mark a specific plan as active.
    """
    try:
        activated = service.activate_plan(plan_id)
        return {
            "status": "success",
            "message": f"Plan {plan_id} activated",
            "id": activated.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}", response_model=List[WeekSchema])
async def get_plan_by_id(
    plan_id: int,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    try:
        return service.get_plan_by_id(plan_id, user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}", response_model=PlanUpdateResponse)
async def update_plan_by_id(
    plan_id: int,
    plan_create: PlanCreate,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    try:
        plan_dicts = [w.model_dump() for w in plan_create.weeks]
        plan = service.update_plan_by_id(
            plan_id,
            plan_dicts,
            user=user,
            title=plan_create.title,
            plan_type=plan_create.type,
            wizard_input=plan_create.wizard_input,
        )
        return {
            "status": "success",
            "message": "Plan updated",
            "id": plan.id,
            "title": plan.title,
            "type": plan.type,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Delete a specific plan.
    """
    try:
        service.delete_plan(plan_id, user)
        return {"status": "success", "message": f"Plan {plan_id} deleted"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan.json", response_model=PlanUpdateResponse)
async def update_plan(
    plan_data: List[WeekSchema],
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Update the active plan for the default user.
    Archives current and creates a new ACTIVE plan version.
    """
    try:
        plan_dicts = [w.model_dump() for w in plan_data]
        new_plan = service.create_or_update_plan(plan_dicts, user=user, activate=True)
        return {
            "status": "success",
            "message": "Plan updated",
            "id": new_plan.id,
            "title": new_plan.title,
            "type": new_plan.type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan.json", response_model=List[WeekSchema])
async def get_plan(
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Get the currently active plan as a list of Weeks.
    """
    return service.get_active_plan(user=user)


@router.put("/weeks/{week_id}")
async def update_week_endpoint(
    week_id: int,
    update_data: WeekUpdate,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Update a specific week (e.g., status).
    """
    try:
        updated = service.update_week(week_id, update_data)
        return {"status": "success", "message": "Week updated", "id": updated.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workouts")
async def create_workout_endpoint(
    workout_create: WorkoutCreate,
    force: bool = False,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Create a new planned workout.
    """
    try:
        new_w = service.add_workout(workout_create, user=user, force=force)
        return {"status": "success", "message": "Workout created", "id": new_w.id}
    except ValidationWarningError as e:
        return JSONResponse(
            status_code=409,
            content={
                "status": "warning",
                "message": e.message,
                "issues": [asdict(i) for i in e.issues],
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workouts/{workout_id}")
async def update_workout_endpoint(
    workout_id: int,
    update_data: WorkoutUpdate,
    force: bool = False,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Update a specific workout (distance, type, description, etc).
    """
    try:
        updated = service.update_workout(workout_id, update_data, force=force)
        return {"status": "success", "message": "Workout updated", "id": updated.id}
    except ValidationWarningError as e:
        return JSONResponse(
            status_code=409,
            content={
                "status": "warning",
                "message": e.message,
                "issues": [asdict(i) for i in e.issues],
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workouts/{workout_id}")
async def delete_workout_endpoint(
    workout_id: int,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Delete a specific planned workout.
    """
    try:
        service.delete_workout(workout_id)
        return {"status": "success", "message": "Workout deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
