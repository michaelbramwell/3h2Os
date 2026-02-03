from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select, delete
from app.core.database import RunnerPlan, PlanWeek, PlanWorkout


def _map_legacy_type_to_new(legacy_type: str) -> tuple[str, str | None]:
    """
    Maps legacy ActivityType string to (new_activity_type, new_workout_format).
    Returns a tuple of (ActivityType value, WorkoutFormat value or None).
    """
    legacy_type_lower = legacy_type.lower()

    # Direct mappings for formats (assuming Run is the default sport)
    format_map = {
        "easy": ("Run", "Easy"),
        "long": ("Run", "Long"),
        "tempo": ("Run", "Tempo"),
        "intervals": ("Run", "Intervals"),
        "race": ("Run", "Race"),
        "recovery": ("Run", "Recovery"),
        "hills": ("Run", "Hills"),
        "steady": ("Run", "Steady"),
        "warmup": ("Run", "WarmUp"),
        "cooldown": ("Run", "CoolDown"),
        "fartlek": ("Run", "Fartlek"),
        "progression": ("Run", "Progression"),
        "time_trial": ("Run", "TimeTrial"),
        "track": ("Run", "Intervals"),
        "plr": ("Run", "Long"),  # Fix for PLR legacy data
        "threshold": ("Run", "Tempo"),  # Fix for Threshold legacy data
    }

    if legacy_type_lower in format_map:
        return format_map[legacy_type_lower]

    # Sport mappings
    sport_map = {
        "run": ("Run", None),
        "running": ("Run", None),
        "trail": ("Trail", None),
        "trail_running": ("Trail", None),
        "cycling": ("Cycling", None),
        "bike": ("Cycling", None),
        "swimming": ("Swimming", None),
        "swim": ("Swimming", None),
        "pool": ("Swimming", None),
        "cross": ("Cross", None),
        "rest": ("Rest", None),
    }

    if legacy_type_lower in sport_map:
        return sport_map[legacy_type_lower]

    # Default fallback
    return ("Run", None)


def plan_to_relational(
    session: Session, plan: RunnerPlan, plan_data_list: List[Dict[str, Any]]
):
    """
    Converts the legacy list-of-dicts plan format into relational tables (PlanWeek, PlanWorkout).
    Wipes existing relational data for this plan first.
    """

    # 1. Clear existing relational data for this plan
    # Use bulk delete logic via fetching week IDs first to avoid N+1 scans or complex subqueries in SQLite
    weeks = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).all()
    week_ids = [w.id for w in weeks]

    if week_ids:
        session.exec(delete(PlanWorkout).where(PlanWorkout.week_id.in_(week_ids)))
        session.exec(delete(PlanWeek).where(PlanWeek.plan_id == plan.id))

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
            status=week_data.get("status", "normal"),
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
                legacy_type = w_data.get("type", "Run")
                # Check if format is explicitly provided (new structure)
                format_val = w_data.get("format")

                if format_val:
                    # New structure: type is likely correct sport, use format directly
                    activity_type = legacy_type
                    workout_format = format_val
                else:
                    # Old structure: map legacy type to new sport + format
                    activity_type, workout_format = _map_legacy_type_to_new(legacy_type)

                workout = PlanWorkout(
                    week_id=week.id,
                    date=day_date,
                    day_name=day_name,
                    name=w_data.get("name", "Unknown"),
                    description=w_data.get("description"),
                    activity_type=activity_type,
                    workout_format=workout_format,
                    distance_m=float(w_data.get("distance_m", 0)),
                    time_of_day=w_data.get("timeOfDay", "AM"),
                )
                session.add(workout)

    session.commit()
    print(f"Relational plan populated for Plan {plan.id}")


def relational_to_plan(session: Session, plan_id: int) -> List[Dict[str, Any]]:
    """
    Queries relational tables and reconstructs the legacy JSON list format.
    """
    weeks = session.exec(
        select(PlanWeek)
        .where(PlanWeek.plan_id == plan_id)
        .order_by(PlanWeek.start_date)
    ).all()

    result = []

    for w in weeks:
        week_dict = {
            "id": w.id,
            "weekStarting": w.start_date.strftime("%Y-%m-%d"),
            "status": w.status,
            "days": {},
        }

        # Initialize empty days for structure consistency (Mon-Sun)
        # This part ensures we return the structure frontend expects even if no workouts
        base_date = w.start_date
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        for i, d_name in enumerate(day_names):
            current_date = base_date + timedelta(days=i)
            week_dict["days"][d_name] = {
                "date": current_date.strftime("%Y-%m-%d"),
                "workouts": [],
            }

        # Fetch workouts
        workouts = session.exec(
            select(PlanWorkout)
            .where(PlanWorkout.week_id == w.id)
            .order_by(PlanWorkout.date)
        ).all()

        for wk in workouts:
            # Reconstruct workout dict
            w_dict = {
                "id": wk.id,
                "name": wk.name,
                "type": wk.activity_type,
                "format": wk.workout_format,
                "distance_m": wk.distance_m,
                "timeOfDay": wk.time_of_day,
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
