from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session
import json
import os
from typing import List, Dict, Any

from app.core.database import get_session
from app.services.plans import PlanService
from app.services.context import ContextService
from app.services.activities import ActivityService
from app.core.validation import ValidationWarningError
from dataclasses import asdict
from app.schemas import (
    WeekSchema, PlanUpdateResponse, ContextSchema, ActivitySchema, PlanCreate, WorkoutUpdate, WorkoutCreate
)
from pydantic import BaseModel

router = APIRouter()

# --- Dependency Injection Functions ---
def get_plan_service(session: Session = Depends(get_session)) -> PlanService:
    return PlanService(session)

def get_context_service(session: Session = Depends(get_session)) -> ContextService:
    return ContextService(session)

def get_activity_service(session: Session = Depends(get_session)) -> ActivityService:
    return ActivityService(session)

class WeightUpdate(BaseModel):
    weight: float

# --- Routes ---

@router.post("/context/weight")
async def update_weight(
    update: WeightUpdate,
    service: ContextService = Depends(get_context_service)
):
    """
    Update the runner's weight (Current & History).
    """
    try:
        new_weight = service.update_weight(update.weight)
        return {"status": "success", "current_weight": new_weight}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/actuals")
async def save_actuals(
    activities: List[ActivitySchema],
    service: ActivityService = Depends(get_activity_service)
):
    """
    Bulk save/update actual activities.
    """
    try:
        count = service.save_activities(activities)
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plans", response_model=PlanUpdateResponse)
async def create_plan(
    plan_create: PlanCreate, 
    service: PlanService = Depends(get_plan_service)
):
    """
    Create a new plan. It is created as inactive by default.
    """
    try:
        plan_dicts = [w.model_dump() for w in plan_create.weeks]
        new_plan = service.create_or_update_plan(
            plan_dicts, 
            username="mike", 
            title=plan_create.title, 
            activate=False
        )
        return {"status": "success", "message": "Plan created", "id": new_plan.id, "title": new_plan.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/plans/{plan_id}/activate")
async def set_active_plan(
    plan_id: int, 
    service: PlanService = Depends(get_plan_service)
):
    """
    Mark a specific plan as active.
    """
    try:
        activated = service.activate_plan(plan_id)
        return {"status": "success", "message": f"Plan {plan_id} activated", "id": activated.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan.json", response_model=PlanUpdateResponse)
async def update_plan(
    plan_data: List[WeekSchema], 
    service: PlanService = Depends(get_plan_service)
):
    """
    Update the active plan for the default user.
    Archives current and creates a new ACTIVE plan version.
    """
    try:
        plan_dicts = [w.model_dump() for w in plan_data]
        new_plan = service.create_or_update_plan(
            plan_dicts, 
            username="mike", 
            activate=True
        )
        return {"status": "success", "message": "Plan updated", "id": new_plan.id, "title": new_plan.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan.json", response_model=List[WeekSchema])
async def get_plan(
    service: PlanService = Depends(get_plan_service)
):
    """
    Get the currently active plan as a list of Weeks.
    """
    return service.get_active_plan(username="mike")

@router.get("/context.json", response_model=ContextSchema)
async def get_context(
    service: ContextService = Depends(get_context_service)
):
    """
    Get the Project and Runner Context.
    """
    return service.get_context(username="mike")

@router.get("/actuals.json", response_model=List[ActivitySchema])
async def get_actuals(
    service: ActivityService = Depends(get_activity_service)
):
    """
    Get the actual activities from the database.
    """
    return service.get_activities()

@router.get("/context/markdown")
async def get_context_markdown():
    """
    Deprecated: Context is now database-driven.
    """
    return {"content": ""}

@router.post("/workouts")
async def create_workout_endpoint(
    workout_create: WorkoutCreate,
    force: bool = False,
    service: PlanService = Depends(get_plan_service)
):
    """
    Create a new planned workout.
    """
    try:
        new_w = service.add_workout(workout_create, username="mike", force=force)
        return {"status": "success", "message": "Workout created", "id": new_w.id}
    except ValidationWarningError as e:
        return JSONResponse(
            status_code=409,
            content={
                "status": "warning",
                "message": e.message,
                "issues": [asdict(i) for i in e.issues]
            }
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
    service: PlanService = Depends(get_plan_service)
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
                "issues": [asdict(i) for i in e.issues]
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/workouts/{workout_id}")
async def delete_workout_endpoint(
    workout_id: int,
    service: PlanService = Depends(get_plan_service)
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
