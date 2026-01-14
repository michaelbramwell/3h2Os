from typing import List, Dict, Any
from datetime import datetime, date, timedelta
from sqlmodel import Session, select
from app.core.database import RunnerPlan, PlanWeek, PlanWorkout

def plan_to_relational(session: Session, plan: RunnerPlan, plan_data_list: List[Dict[str, Any]]):
    """
    Converts the legacy list-of-dicts plan format into relational tables (PlanWeek, PlanWorkout).
    Wipes existing relational data for this plan first.
    """
    
    # 1. Clear existing relational data for this plan
    # Note: Cascades usually handle this if configured, but explicit is safe
    weeks = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).all()
    for w in weeks:
        # Delete workouts for this week
        workouts = session.exec(select(PlanWorkout).where(PlanWorkout.week_id == w.id)).all()
        for wk in workouts:
            session.delete(wk)
        session.delete(w)
    
    session.commit()
    
    # 2. Parse and Insert
    for week_data in plan_data_list:
        start_date_str = week_data.get("weekStarting")
        if not start_date_str:
            continue
            
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
        # Create Week
        week = PlanWeek(
            plan_id=plan.id,
            start_date=start_date,
            status=week_data.get("status", "normal")
        )
        session.add(week)
        session.commit()
        session.refresh(week)
        
        # Create Workouts
        days_map = week_data.get("days", {})
        for day_name, day_data in days_map.items():
            day_date_str = day_data.get("date")
            if not day_date_str:
                # Fallback? Calculate from start_date + offset
                continue
            
            day_date = datetime.strptime(day_date_str, "%Y-%m-%d").date()
            
            workouts_list = day_data.get("workouts", [])
            for w_data in workouts_list:
                workout = PlanWorkout(
                    week_id=week.id,
                    date=day_date,
                    day_name=day_name,
                    name=w_data.get("name", "Unknown"),
                    description=w_data.get("description"),
                    activity_type=w_data.get("type", "Run"),
                    distance_m=float(w_data.get("distance_m", 0)),
                    time_of_day=w_data.get("timeOfDay", "AM")
                )
                session.add(workout)
                
    session.commit()
    print(f"Relational plan populated for Plan {plan.id}")

def relational_to_plan(session: Session, plan_id: int) -> List[Dict[str, Any]]:
    """
    Queries relational tables and reconstructs the legacy JSON list format.
    """
    weeks = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan_id).order_by(PlanWeek.start_date)).all()
    
    result = []
    
    for w in weeks:
        week_dict = {
            "weekStarting": w.start_date.strftime("%Y-%m-%d"),
            "status": w.status,
            "days": {}
        }
        
        # Initialize empty days for structure consistency (Mon-Sun)
        # This part ensures we return the structure frontend expects even if no workouts
        base_date = w.start_date
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for i, d_name in enumerate(day_names):
            current_date = base_date + timedelta(days=i)
            week_dict["days"][d_name] = {
                "date": current_date.strftime("%Y-%m-%d"),
                "workouts": []
            }
            
        # Fetch workouts
        workouts = session.exec(select(PlanWorkout).where(PlanWorkout.week_id == w.id).order_by(PlanWorkout.date)).all()
        
        for wk in workouts:
            # Reconstruct workout dict
            w_dict = {
                "name": wk.name,
                "type": wk.activity_type,
                "distance_m": wk.distance_m,
                "timeOfDay": wk.time_of_day
            }
            if wk.description:
                w_dict["description"] = wk.description
                
            # Add to correct day bucket
            # We trust the date in the DB mostly
            # Find the key in the map that matches the date
            target_key = None
            for d_key, d_val in week_dict["days"].items():
                if d_val["date"] == wk.date.strftime("%Y-%m-%d"):
                    target_key = d_key
                    break
            
            if target_key:
                week_dict["days"][target_key]["workouts"].append(w_dict)
                
        result.append(week_dict)
        
    return result
