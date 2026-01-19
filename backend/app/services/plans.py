from sqlmodel import Session, select
from datetime import datetime, date, timedelta
import json
from typing import List, Dict, Any

from app.core.database import RunnerPlan, User, PlanWeek, PlanWorkout, ActualActivity
from app.core.mappers import plan_to_relational, relational_to_plan
from app.schemas import WeekSchema, WorkoutUpdate, WorkoutCreate
from app.core.validation import ValidationEngine, ValidationWarningError
from app.models.domain import Week as DomainWeek, Day as DomainDay, Workout as DomainWorkout

class PlanService:
    def __init__(self, session: Session):
        self.session = session
        self.validator = ValidationEngine()

    def _create_domain_week(self, plan_week: PlanWeek, updated_workouts: List[PlanWorkout] = None) -> DomainWeek:
        # If no updated list is provided, fetch from DB
        if updated_workouts is None:
             updated_workouts = self.session.exec(
                 select(PlanWorkout).where(PlanWorkout.week_id == plan_week.id)
             ).all()
        
        # Group by Day Name
        days_map = {k: [] for k in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
        
        week_start = plan_week.start_date
        
        # Populate workouts
        for w in updated_workouts:
            d_work = DomainWorkout(
                name=w.name,
                type=w.activity_type,
                distance_m=w.distance_m,
                timeOfDay=w.time_of_day
            )
            # Find which day index
            if not w.date: continue
            days_diff = (w.date - week_start).days
            day_keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            if 0 <= days_diff < 7:
                 days_map[day_keys[days_diff]].append(d_work)
            
        # Build Domain Days
        domain_days = {}
        day_keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, key in enumerate(day_keys):
            d_date = week_start + timedelta(days=i)
            domain_days[key] = DomainDay(
                 date=d_date.isoformat(),
                 workouts=days_map[key]
            )
            
        return DomainWeek(
            weekStarting=week_start.isoformat(),
            status=plan_week.status,
            days=domain_days
        )

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

    def delete_workout(self, workout_id: int) -> None:
        """
        Deletes a specific planned workout.
        """
        workout = self.session.get(PlanWorkout, workout_id)
        if not workout:
            raise ValueError(f"Workout with ID {workout_id} not found")

        # Prevent editing past workouts
        if workout.date < date.today():
             raise ValueError("Cannot delete workouts that have already occurred")
        
        self.session.delete(workout)
        self.session.commit()

    def update_workout(self, workout_id: int, update_data: WorkoutUpdate, force: bool = False) -> PlanWorkout:
        """
        Updates a specific planned workout.
        """
        workout = self.session.get(PlanWorkout, workout_id)
        if not workout:
            raise ValueError(f"Workout with ID {workout_id} not found")

        # Prevent editing past workouts
        if workout.date < date.today():
             raise ValueError("Cannot edit workouts that have already occurred")
        
        # Validation Logic (Progression / Safety)
        if not force:
            target_week = self.session.get(PlanWeek, workout.week_id)
            
            # 1. Get Previous Week
            prev_week_start = target_week.start_date - timedelta(days=7)
            prev_week = self.session.exec(
                select(PlanWeek)
                .where(PlanWeek.plan_id == target_week.plan_id)
                .where(PlanWeek.start_date == prev_week_start)
            ).first()
            
            # 2. Get Current Workouts (DB)
            current_workouts = self.session.exec(
                select(PlanWorkout).where(PlanWorkout.week_id == target_week.id)
            ).all()
            
            # 3. Simulate Change
            simulated_workouts = []
            for w in current_workouts:
                if w.id == workout_id:
                    # Create a detached copy with updates
                    # Note: model_dump might not include ID if not in schema, but we copy state
                    updated_w = PlanWorkout(**w.model_dump()) 
                    # Set ID explicitly to match logically, though detached
                    updated_w.id = w.id
                    
                    update_dict = update_data.model_dump(exclude_unset=True)
                    if "type" in update_dict: updated_w.activity_type = update_dict.pop("type")
                    if "timeOfDay" in update_dict: updated_w.time_of_day = update_dict.pop("timeOfDay")
                    for k,v in update_dict.items():
                        if hasattr(updated_w, k): setattr(updated_w, k, v)
                    simulated_workouts.append(updated_w)
                else:
                    simulated_workouts.append(w)
            
            # 4. Create Domain Weeks
            domain_curr = self._create_domain_week(target_week, simulated_workouts)
            domain_prev = self._create_domain_week(prev_week) if prev_week else DomainWeek(
                weekStarting="1970-01-01", status="normal", days={}
            )
            
            # 5. Validate
            # We construct a Domain Workout object to represent the "Focused" workout (the one being edited)
            # This allows the validator to filter warnings to just this activity.
            target_workout = next(w for w in simulated_workouts if w.id == workout_id)
            domain_focused_workout = DomainWorkout(
                name=target_workout.name,
                type=target_workout.activity_type,
                distance_m=target_workout.distance_m,
                timeOfDay=target_workout.time_of_day
            )

            issues = self.validator.validate_progression(domain_prev, domain_curr, focused_workout=domain_focused_workout)
            if issues:
                raise ValidationWarningError(issues)

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

    def add_workout(self, creation_data: WorkoutCreate, username: str = "mike", force: bool = False) -> PlanWorkout:
        """
        Adds a new workout to the active plan.
        """
        # 1. Get Active Plan
        statement = select(RunnerPlan).join(User).where(User.username == username).where(RunnerPlan.is_active == True)
        plan = self.session.exec(statement).first()
        if not plan:
             raise ValueError("No active plan found for user")

        target_date = creation_data.date
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        # 2. Find correct Week (Monday start)
        week_start = target_date - timedelta(days=target_date.weekday())
        
        week = self.session.exec(
            select(PlanWeek)
            .where(PlanWeek.plan_id == plan.id)
            .where(PlanWeek.start_date == week_start)
        ).first()
        
        if not week:
            # Create a new week if it doesn't exist
            week = PlanWeek(
                plan_id=plan.id,
                start_date=week_start,
                status="normal"
            )
            self.session.add(week)
            self.session.commit()
            self.session.refresh(week)

        # 2b. Validation Logic
        if not force:
            # Get Previous Week
            prev_week_start = week_start - timedelta(days=7)
            prev_week = self.session.exec(
                select(PlanWeek)
                .where(PlanWeek.plan_id == plan.id)
                .where(PlanWeek.start_date == prev_week_start)
            ).first()

            # Create simulated workout list
            current_workouts = self.session.exec(
                 select(PlanWorkout).where(PlanWorkout.week_id == week.id)
            ).all()
            
            temp_day_name = day_names[target_date.weekday()]
            
            temp_new_workout = PlanWorkout(
                week_id=week.id,
                date=target_date,
                day_name=temp_day_name,
                name=creation_data.name,
                description=creation_data.description,
                activity_type=creation_data.type,
                distance_m=creation_data.distance_m,
                time_of_day=creation_data.timeOfDay
            )
            simulated_workouts = list(current_workouts) + [temp_new_workout]

            domain_curr = self._create_domain_week(week, simulated_workouts)
            domain_prev = self._create_domain_week(prev_week) if prev_week else DomainWeek(
                weekStarting="1970-01-01", status="normal", days={}
            )
            
            # Construct Domain Workout for focus
            domain_focused_workout = DomainWorkout(
                name=temp_new_workout.name,
                type=temp_new_workout.activity_type,
                distance_m=temp_new_workout.distance_m,
                timeOfDay=temp_new_workout.time_of_day
            )

            issues = self.validator.validate_progression(domain_prev, domain_curr, focused_workout=domain_focused_workout)
            if issues:
                raise ValidationWarningError(issues)

        # 3. Create Workout
        # day_names defined above
        day_name = day_names[target_date.weekday()]

        new_workout = PlanWorkout(
            week_id=week.id,
            date=target_date,
            day_name=day_name,
            name=creation_data.name,
            description=creation_data.description,
            activity_type=creation_data.type,
            distance_m=creation_data.distance_m,
            time_of_day=creation_data.timeOfDay
        )
        
        self.session.add(new_workout)
        self.session.commit()
        self.session.refresh(new_workout)
        return new_workout

    def _deactivate_current_plans(self, user_id: int, exclude_id: int = None):
        statement = select(RunnerPlan).where(RunnerPlan.user_id == user_id).where(RunnerPlan.is_active == True)
        active_plans = self.session.exec(statement).all()
        for p in active_plans:
            if exclude_id and p.id == exclude_id:
                continue
            p.is_active = False
            self.session.add(p)
