from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
import json
import os
from app.core.database import get_session, User, RunnerPlan

router = APIRouter()

@router.get("/plan.json")
async def get_plan(session: Session = Depends(get_session)):
    # Simple logic: get the active plan for user "mike" (hardcoded for now)
    statement = select(RunnerPlan).join(User).where(User.username == "mike").where(RunnerPlan.is_active == True)
    plan = session.exec(statement).first()
    
    if plan:
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
