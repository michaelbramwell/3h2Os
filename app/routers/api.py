from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
import json
import os
from typing import List, Dict, Any
from app.core.database import get_session, User, RunnerPlan, PlanWeek
from app.core.services import save_plan_to_db
from app.core.mappers import relational_to_plan

router = APIRouter()

@router.post("/plan.json")
async def update_plan(plan_data: List[Dict[str, Any]], session: Session = Depends(get_session)):
    """
    Update the active plan for the default user.
    Accepts a JSON body representing the list of weeks.
    """
    try:
        # Assuming single user for now, or auth could be added later
        new_plan = save_plan_to_db(plan_data, session, username="mike")
        return {"status": "success", "message": "Plan updated", "id": new_plan.id, "title": new_plan.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan.json")
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
                return JSONResponse(content=relational_to_plan(session, plan.id))
            except Exception as e:
                print(f"Error reading relational plan: {e}. Falling back to blob.")
                
        # Fallback to blob
        return JSONResponse(content=json.loads(plan.plan_json))
    
    # Fallback to file if DB empty or issue
    if os.path.exists("data/plan.json"):
        with open("data/plan.json", "r") as f:
            return JSONResponse(content=json.load(f))
    return []

@router.get("/context.json")
async def get_context():
    if os.path.exists("data/context.json"):
        with open("data/context.json", "r") as f:
            return JSONResponse(content=json.load(f))
    return {}

@router.get("/actuals.json")
async def get_actuals():
    if os.path.exists("data/actuals.json"):
        with open("data/actuals.json", "r") as f:
            return JSONResponse(content=json.load(f))
    return []
