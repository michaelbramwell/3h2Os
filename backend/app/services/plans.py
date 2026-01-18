from sqlmodel import Session, select
from datetime import datetime, date
import json
import os
from typing import List, Dict, Any

from app.core.database import RunnerPlan, User, PlanWeek, PlanWorkout, ActualActivity
from app.core.mappers import plan_to_relational, relational_to_plan
from app.schemas import WeekSchema, WorkoutUpdate

class PlanService:
    def __init__(self, session: Session):
        self.session = session

    def get_active_plan(self, username: str = "mike") -> List[WeekSchema]:
        """
        Retrieves the active plan for the user.
        Prioritizes Relational DB -> JSON Blob in DB -> JSON File.
        """
        statement = select(RunnerPlan).join(User).where(User.username == username).where(RunnerPlan.is_active == True)
        plan = self.session.exec(statement).first()
        
        plan_data = []
        
        if plan:
            # 1. Try Relational tables
            has_relational = self.session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).first()
            if has_relational:
                try:
                    plan_data = relational_to_plan(self.session, plan.id)
                except Exception as e:
                    print(f"Error reading relational plan: {e}. Falling back to blob.")
                    plan_data = json.loads(plan.plan_json)
            else:
                # 2. Fallback to Blob
                plan_data = json.loads(plan.plan_json)
        
        return [WeekSchema.model_validate(w) for w in plan_data]

    def create_or_update_plan(self, plan_data: List[Dict[str, Any]], username: str = "mike", title: str = None, activate: bool = False) -> RunnerPlan:
        """
        Creates a new plan version. Optionally activates it.
        """
        # Ensure user exists
        user = self.session.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f"User '{username}' not found. Creating...")
            user = User(username=username, email=f"{username}@example.com")
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)

        if activate:
            self._deactivate_current_plans(user.id)
        
        if not title:
            title = f"Plan Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        new_plan = RunnerPlan(
            title=title,
            is_active=activate,
            plan_json=json.dumps(plan_data),
            user_id=user.id
        )
        self.session.add(new_plan)
        self.session.commit()
        self.session.refresh(new_plan)
        
        try:
            plan_to_relational(self.session, new_plan, plan_data)
        except Exception as e:
            print(f"Error populating relational tables: {e}")
            
        return new_plan

    def activate_plan(self, plan_id: int) -> RunnerPlan:
        """
        Activates a specific plan ID and deactivates others.
        """
        plan = self.session.get(RunnerPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
            
        self._deactivate_current_plans(plan.user_id, exclude_id=plan.id)
            
        plan.is_active = True
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def update_workout(self, workout_id: int, update_data: WorkoutUpdate) -> PlanWorkout:
        """
        Updates a specific planned workout.
        """
        workout = self.session.get(PlanWorkout, workout_id)
        if not workout:
            raise ValueError(f"Workout with ID {workout_id} not found")

        # Prevent editing past workouts
        if workout.date < date.today():
             raise ValueError("Cannot edit workouts that have already occurred")

        # Check for completed actuals today
        if workout.date == date.today():
             # Navigate relationship to find user_id: Workout -> Week -> Plan -> User
             # Note: We need to ensure relationships are loaded or query directly with join
             statement = (
                 select(ActualActivity)
                 .join(User)
                 .join(RunnerPlan)
                 .join(PlanWeek)
                 .join(PlanWorkout)
                 .where(PlanWorkout.id == workout_id)
                 .where(ActualActivity.date == workout.date)
             )
             # Simplify: Just assume if any activity exists for this day for this user?
             # But we need user_id. workout -> week -> plan -> user_id
             # Let's just load the week.plan relationship since it's likely not eagerly loaded
             # Re-fetch workout with relationships or multiple queries?
             pass 
             # Simpler approach:
             week = self.session.get(PlanWeek, workout.week_id)
             if week:
                 plan = self.session.get(RunnerPlan, week.plan_id)
                 if plan:
                     actuals = self.session.exec(
                         select(ActualActivity)
                         .where(ActualActivity.user_id == plan.user_id)
                         .where(ActualActivity.date == workout.date)
                     ).all()
                     if actuals:
                         raise ValueError("Cannot edit workouts that have already occurred (Activity logged)")

        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Handle field name mismatches (Schema vs DB)
        if "type" in update_dict:
            workout.activity_type = update_dict.pop("type")
        if "timeOfDay" in update_dict:
            workout.time_of_day = update_dict.pop("timeOfDay")
            
        # Update remaining fields
        for key, value in update_dict.items():
            if hasattr(workout, key):
                setattr(workout, key, value)
            
        self.session.add(workout)
        self.session.commit()
        self.session.refresh(workout)
        return workout

    def _deactivate_current_plans(self, user_id: int, exclude_id: int = None):
        statement = select(RunnerPlan).where(RunnerPlan.user_id == user_id).where(RunnerPlan.is_active == True)
        active_plans = self.session.exec(statement).all()
        for p in active_plans:
            if exclude_id and p.id == exclude_id:
                continue
            p.is_active = False
            self.session.add(p)
