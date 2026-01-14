from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
import json
import os
from typing import List, Dict, Any
from app.core.services import save_plan_to_db, activate_plan

# ... [keep imports]
from app.core.database import get_session, User, RunnerPlan, PlanWeek
from app.core.mappers import relational_to_plan
from app.schemas import WeekSchema, PlanUpdateResponse, ContextSchema, ActivitySchema, PlanCreate

router = APIRouter()

@router.post("/plans", response_model=PlanUpdateResponse)
async def create_plan(plan_create: PlanCreate, session: Session = Depends(get_session)):
    """
    Create a new plan. It is created as inactive by default.
    """
    try:
        # Convert Pydantic models to list of dicts for the service
        plan_dicts = [w.model_dump() for w in plan_create.weeks]
        new_plan = save_plan_to_db(plan_dicts, session, username="mike", title=plan_create.title, activate=False)
        return {"status": "success", "message": "Plan created", "id": new_plan.id, "title": new_plan.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/plans/{plan_id}/activate")
async def set_active_plan(plan_id: int, session: Session = Depends(get_session)):
    """
    Mark a specific plan as active.
    """
    try:
        activated = activate_plan(plan_id, session)
        return {"status": "success", "message": f"Plan {plan_id} activated", "id": activated.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/plan.json", response_model=PlanUpdateResponse)
async def update_plan(plan_data: List[WeekSchema], session: Session = Depends(get_session)):
    """
    Update the active plan for the default user.
    Archives current and creates a new ACTIVE plan version.
    """
    try:
        # Convert Pydantic models to list of dicts for the service
        plan_dicts = [w.model_dump() for w in plan_data]
        # Assuming single user for now, or auth could be added later
        new_plan = save_plan_to_db(plan_dicts, session, username="mike", activate=True)
        return {"status": "success", "message": "Plan updated", "id": new_plan.id, "title": new_plan.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    """
    Update the active plan for the default user.
    Accepts a JSON body representing the list of weeks.
    """
    try:
        # Convert Pydantic models to list of dicts for the service
        plan_dicts = [w.model_dump() for w in plan_data]
        # Assuming single user for now, or auth could be added later
        new_plan = save_plan_to_db(plan_dicts, session, username="mike")
        return {"status": "success", "message": "Plan updated", "id": new_plan.id, "title": new_plan.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan.json", response_model=List[WeekSchema])
async def get_plan(session: Session = Depends(get_session)):
    # Simple logic: get the active plan for user "mike" (hardcoded for now)
    statement = select(RunnerPlan).join(User).where(User.username == "mike").where(RunnerPlan.is_active == True)
    plan = session.exec(statement).first()
    
    if plan:
        # Try to read from relational tables first
        # Check if relational data exists
        has_relational = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).first()
        
        if has_relational:
            try:
                # Reconstruct from relational
                return relational_to_plan(session, plan.id)
            except Exception as e:
                print(f"Error reading relational plan: {e}. Falling back to blob.")
                
        # Fallback to blob
        return json.loads(plan.plan_json)
    
    # Fallback to file if DB empty or issue
    if os.path.exists("data/plan.json"):
        with open("data/plan.json", "r") as f:
            return json.load(f)
    return []

@router.get("/context.json", response_model=ContextSchema)
async def get_context():
    if os.path.exists("data/context.json"):
        with open("data/context.json", "r") as f:
            return json.load(f)
    return {}

@router.get("/actuals.json", response_model=List[ActivitySchema])
async def get_actuals():
    if os.path.exists("data/actuals.json"):
        with open("data/actuals.json", "r") as f:
            return json.load(f)
    return []
