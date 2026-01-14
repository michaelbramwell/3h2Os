from datetime import datetime
import json
from sqlmodel import Session, select
from app.core.database import RunnerPlan, User
from app.core.mappers import plan_to_relational
from typing import List, Dict, Any

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
