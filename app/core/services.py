from datetime import datetime
import json
import os
from sqlmodel import Session, select
from app.core.database import RunnerPlan, User, PlanWeek
from app.core.mappers import relational_to_plan, plan_to_relational
from app.schemas import (
    WeekSchema, ContextSchema, ProjectContext, RunnerContext, 
    WeightContext, WeightRecord, PlanUpdateResponse
)
from typing import List, Dict, Any, Optional

def get_context_dto(session: Session, username: str = "mike") -> ContextSchema:
    """
    Retrieves the context (Project, Runner Profile) for a user and maps it to the ContextSchema DTO.
    Fallback to file if DB is empty.
    """
    # Try fetching from DB first
    user = session.exec(select(User).where(User.username == username)).first()
    if user and user.project and user.profile:
        # 1. Project (automapped via from_attributes=True + aliases)
        project_ctx = ProjectContext.model_validate(user.project)

        # 2. Weights (manual map due to DB renaming/structure)
        weights = [
            WeightRecord(date=str(w.date_recorded), weight=w.weight_kg) 
            for w in sorted(user.profile.weight_history, key=lambda x: x.date_recorded)
        ]
        
        weight_ctx = WeightContext(
            current=user.profile.current_weight,
            target=user.profile.target_weight,
            history=weights
        )

        # 3. Runner (mix of automap properties + custom nested object)
        runner_ctx = RunnerContext(
            age=user.profile.age,
            gender=user.profile.gender,
            height_cm=user.profile.height_cm,
            weight_kg=weight_ctx
        )

        return ContextSchema(project=project_ctx, runner=runner_ctx)

    # Fallback
    if os.path.exists("data/context.json"):
        with open("data/context.json", "r") as f:
            return ContextSchema.model_validate(json.load(f))
    return ContextSchema(
        project=ProjectContext(name="", goal="", event="", eventDate=""),
        runner=RunnerContext(age=0, gender="", height_cm=0, weight_kg=WeightContext(current=0, target=0))
    )

def get_active_plan_dto(session: Session, username: str = "mike") -> List[WeekSchema]:
    """
    Retrieves the active plan for the user and maps it to List[WeekSchema].
    """
    statement = select(RunnerPlan).join(User).where(User.username == username).where(RunnerPlan.is_active == True)
    plan = session.exec(statement).first()
    
    plan_data = []
    
    if plan:
        # Try to read from relational tables first
        has_relational = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).first()
        
        if has_relational:
            try:
                # Reconstruct from relational (returns list of dicts)
                plan_data = relational_to_plan(session, plan.id)
            except Exception as e:
                print(f"Error reading relational plan: {e}. Falling back to blob.")
                plan_data = json.loads(plan.plan_json)
        else:
             # Fallback to blob
            plan_data = json.loads(plan.plan_json)
    
    elif os.path.exists("data/plan.json"):
        # Fallback to file if DB empty
        with open("data/plan.json", "r") as f:
            plan_data = json.load(f)
            
    # Convert list of dicts to list of Pydantic models (DTOs)
    # Pydantic's adapter or list comprehension works here
    return [WeekSchema.model_validate(w) for w in plan_data]

def save_plan_to_db(plan_data: List[Dict[str, Any]], session: Session, username: str = "mike", title: str = None, activate: bool = False) -> RunnerPlan:
    """
    Saves the provided plan data (list of weeks/dicts) to the database.
    If activate=True, archives any existing active plans for the user and makes this one active.
    Creates the user if they don't exist.
    Uses the provided SQLModel Session.
    """
    # Check for user
    user = session.exec(select(User).where(User.username == username)).first()
    
    if not user:
        # Create user if missing
        print(f"User '{username}' not found. Creating...")
        user = User(username=username, email=f"{username}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

    if activate:
        # Deactivate all current active plans
        active_plans = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == user.id).where(RunnerPlan.is_active == True)).all()
        if active_plans:
            # print(f"Archiving {len(active_plans)} active plan(s)...") 
            for p in active_plans:
                p.is_active = False
                session.add(p)
    
    if not title:
        title = f"Plan Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Create new plan
    new_plan = RunnerPlan(
        title=title,
        is_active=activate,
        plan_json=json.dumps(plan_data), # Keep legacy blob for backup/debug
        user_id=user.id
    )
    session.add(new_plan)
    session.commit()
    session.refresh(new_plan)
    
    # Populate Relational Tables
    try:
        plan_to_relational(session, new_plan, plan_data)
    except Exception as e:
        print(f"Error populating relational tables: {e}")
        # Non-fatal for now alongside JSON
        
    return new_plan

def activate_plan(plan_id: int, session: Session) -> RunnerPlan:
    """
    Sets the specified plan to active and deactivates all other plans for the same user.
    """
    plan = session.get(RunnerPlan, plan_id)
    if not plan:
        raise ValueError(f"Plan with ID {plan_id} not found")
        
    # Deactivate others for same user
    active_plans = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == plan.user_id).where(RunnerPlan.is_active == True)).all()
    for p in active_plans:
        if p.id != plan.id:
            p.is_active = False
            session.add(p)
            
    plan.is_active = True
    session.add(plan)
    session.commit()
    session.refresh(plan)
    return plan
