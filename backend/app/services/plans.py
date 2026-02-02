from sqlmodel import Session, select
from datetime import datetime, date, timedelta
import json
import os
from typing import List, Dict, Any

from app.core import plan_logic
from app.core.database import RunnerPlan, User, PlanWeek, PlanWorkout, ActualActivity
from app.core.mappers import plan_to_relational, relational_to_plan
from app.schemas import WeekSchema, WorkoutUpdate, WorkoutCreate, WeekUpdate
from app.core.validation import ValidationEngine, ValidationWarningError
from app.models.domain import (
    Week as DomainWeek,
    Day as DomainDay,
    Workout as DomainWorkout,
)


class PlanService:
    def __init__(self, session: Session):
        self.session = session
        self.validator = ValidationEngine()

    def get_active_plan(self, user: User = None) -> List[WeekSchema]:
        """
        Retrieves the active plan for the user.
        Prioritizes Relational DB -> JSON Blob in DB -> JSON File.
        """
        if user:
            statement = (
                select(RunnerPlan)
                .where(RunnerPlan.user_id == user.id)
                .where(RunnerPlan.is_active == True)
            )
        else:
            username = os.environ.get("DEFAULT_USERNAME", "runner")
            statement = (
                select(RunnerPlan)
                .join(User)
                .where(User.username == username)
                .where(RunnerPlan.is_active == True)
            )

        plan = self.session.exec(statement).first()

        plan_data = []

        if plan:
            # 1. Try Relational tables
            has_relational = self.session.exec(
                select(PlanWeek).where(PlanWeek.plan_id == plan.id)
            ).first()
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

    def get_plans(self, user: User) -> List[RunnerPlan]:
        """
        Retrieves all plans for the user.
        """
        statement = select(RunnerPlan).where(RunnerPlan.user_id == user.id)
        return self.session.exec(statement).all()

    def create_or_update_plan(
        self,
        plan_data: List[Dict[str, Any]],
        user: User = None,
        title: str = None,
        plan_type: str = "running",
        activate: bool = False,
    ) -> RunnerPlan:
        """
        Creates a new plan version. Optionally activates it.
        """
        if not user:
            username = os.environ.get("DEFAULT_USERNAME", "runner")
            # Ensure user exists
            user = self.session.exec(
                select(User).where(User.username == username)
            ).first()
            if not user:
                print(f"User '{username}' not found. Creating...")
                user = User(username=username, email=f"{username}@example.com")
                self.session.add(user)
                self.session.commit()
                self.session.refresh(user)

        if activate:
            self._deactivate_current_plans(user.id)
        else:
            # Auto-activate if it's the user's first plan
            existing_plans = self.session.exec(
                select(RunnerPlan).where(RunnerPlan.user_id == user.id)
            ).all()
            if not existing_plans:
                activate = True

        if not title:
            title = f"Plan Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        new_plan = RunnerPlan(
            title=title,
            type=plan_type,
            is_active=activate,
            plan_json=json.dumps(plan_data),
            user_id=user.id,
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

    def _validate_progression_safely(
        self,
        week: PlanWeek,
        simulated_workouts: List[PlanWorkout],
        focused_workout: PlanWorkout,
    ):
        """Helper to validate plan progression changes"""
        # 1. Get Previous Week
        prev_week_start = week.start_date - timedelta(days=7)
        prev_week = self.session.exec(
            select(PlanWeek)
            .where(PlanWeek.plan_id == week.plan_id)
            .where(PlanWeek.start_date == prev_week_start)
        ).first()

        prev_workouts = []
        prev_status = "normal"
        if prev_week:
            prev_workouts = self.session.exec(
                select(PlanWorkout).where(PlanWorkout.week_id == prev_week.id)
            ).all()
            prev_status = prev_week.status

        # 2. Prepare Data via Pure Logic
        domain_prev, domain_curr, domain_focused = plan_logic.prepare_validation_data(
            target_week_start=week.start_date,
            target_week_status=week.status,
            target_workouts=simulated_workouts,
            focused_workout=focused_workout,
            prev_week_start=prev_week_start,
            prev_week_status=prev_status,
            prev_week_workouts=prev_workouts,
        )

        # 3. Validate
        issues = self.validator.validate_progression(
            domain_prev, domain_curr, focused_workout=domain_focused
        )
        if issues:
            raise ValidationWarningError(issues)

    def update_week(self, week_id: int, update_data: WeekUpdate) -> PlanWeek:
        """
        Updates a specific plan week (e.g. status).
        """
        week = self.session.get(PlanWeek, week_id)
        if not week:
            raise ValueError(f"Week with ID {week_id} not found")

        if update_data.status:
            week.status = update_data.status

        # We don't generally allow changing weekStarting as it breaks chronology easily,
        # but could be added if needed with heavy validation.

        self.session.add(week)
        self.session.commit()
        self.session.refresh(week)
        return week

    def update_workout(
        self, workout_id: int, update_data: WorkoutUpdate, force: bool = False
    ) -> PlanWorkout:
        """
        Updates a specific planned workout.
        """
        workout = self.session.get(PlanWorkout, workout_id)
        if not workout:
            raise ValueError(f"Workout with ID {workout_id} not found")

        # Prevent editing past workouts
        if not force and workout.date < date.today():
            raise ValueError("Cannot edit workouts that have already occurred")

        # Validation Logic (Progression / Safety)
        if not force:
            target_week = self.session.get(PlanWeek, workout.week_id)
            current_workouts = self.session.exec(
                select(PlanWorkout).where(PlanWorkout.week_id == target_week.id)
            ).all()

            # Simulate Change
            simulated_workouts = []
            target_simulated = None

            print(
                f"DEBUG: Updating workout_id={workout_id}. UpdateData={update_data.model_dump(exclude_unset=True)}"
            )

            for w in current_workouts:
                if w.id == workout_id:
                    print(
                        f"DEBUG: Found workout match! ID={w.id}. Current Dist={w.distance_m}"
                    )
                    # Create a detached copy with updates
                    updated_w = PlanWorkout(**w.model_dump())
                    updated_w.id = w.id  # Keep ID for logic

                    data = update_data.model_dump(exclude_unset=True)
                    plan_logic.apply_workout_updates(updated_w, data)

                    print(f"DEBUG: Updated Dist={updated_w.distance_m}")

                    simulated_workouts.append(updated_w)
                    target_simulated = updated_w
                else:
                    simulated_workouts.append(w)

            if not target_simulated:
                print(
                    f"DEBUG: CRITICAL - No workout matched ID {workout_id} in current_workouts list: {[w.id for w in current_workouts]}"
                )

            self._validate_progression_safely(
                target_week, simulated_workouts, target_simulated
            )

        # Check for completed actuals today
        if not force and workout.date == date.today():
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
                        raise ValueError(
                            "Cannot edit workouts that have already occurred (Activity logged)"
                        )

        # Apply actual updates
        data = update_data.model_dump(exclude_unset=True)
        plan_logic.apply_workout_updates(workout, data)

        self.session.add(workout)
        self.session.commit()
        self.session.refresh(workout)
        return workout

    def add_workout(
        self, creation_data: WorkoutCreate, user: User = None, force: bool = False
    ) -> PlanWorkout:
        """
        Adds a new workout to the active plan.
        """
        if not user:
            username = os.environ.get("DEFAULT_USERNAME", "runner")
            # 1. Get Active Plan
            statement = (
                select(RunnerPlan)
                .join(User)
                .where(User.username == username)
                .where(RunnerPlan.is_active == True)
            )
        else:
            statement = (
                select(RunnerPlan)
                .where(RunnerPlan.user_id == user.id)
                .where(RunnerPlan.is_active == True)
            )

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
            week = PlanWeek(plan_id=plan.id, start_date=week_start, status="normal")
            self.session.add(week)
            self.session.commit()
            self.session.refresh(week)

        day_name = day_names[target_date.weekday()]

        # Prepare new workout object (not yet added to session)
        new_workout = PlanWorkout(
            week_id=week.id,
            date=target_date,
            day_name=day_name,
            name=creation_data.name,
            description=creation_data.description,
            activity_type=creation_data.type,
            distance_m=creation_data.distance_m,
            time_of_day=creation_data.timeOfDay,
        )

        # 2b. Validation Logic
        if not force:
            current_workouts = self.session.exec(
                select(PlanWorkout).where(PlanWorkout.week_id == week.id)
            ).all()
            simulated_workouts = list(current_workouts) + [new_workout]

            self._validate_progression_safely(week, simulated_workouts, new_workout)

        # 3. Create Workout
        self.session.add(new_workout)
        self.session.commit()
        self.session.refresh(new_workout)
        return new_workout

    def _deactivate_current_plans(self, user_id: int, exclude_id: int = None):
        statement = (
            select(RunnerPlan)
            .where(RunnerPlan.user_id == user_id)
            .where(RunnerPlan.is_active == True)
        )
        active_plans = self.session.exec(statement).all()
        for p in active_plans:
            if exclude_id and p.id == exclude_id:
                continue
            p.is_active = False
            self.session.add(p)

    def _get_last_actual_volume(
        self, user: User, current_week_start: datetime
    ) -> float:
        # Fetch actuals for the week PRIOR to current_week_start
        prev_week_start = current_week_start - timedelta(days=7)
        prev_week_end = current_week_start - timedelta(seconds=1)

        # Query ActualActivity directly
        activities = self.session.exec(
            select(ActualActivity)
            .where(ActualActivity.user_id == user.id)
            .where(ActualActivity.date >= prev_week_start.date())
            .where(ActualActivity.date <= prev_week_end.date())
        ).all()

        total = 0.0
        for act in activities:
            # Filter types - Include Swimming for volume calculation
            # Note: We might want to separate Running Volume vs Swimming Volume in future,
            # but for now, we just sum up the distance of the PRIMARY activity of the plan.
            # Ideally we check the Plan Type, but here we just allow both.
            if act.type in ["running", "trail_running", "swimming", "swim", "pool"]:
                total += act.distance_m
        return total

    def delete_plan(self, plan_id: int, user: User) -> None:
        """
        Deletes a specific plan and its associated data.
        Cannot delete the active plan unless it's the only one (handled by frontend logic mostly, but good to check).
        """
        plan = self.session.get(RunnerPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")

        if plan.user_id != user.id:
            raise ValueError("Cannot delete a plan that does not belong to you")

        # Cascade delete is usually handled by DB, but explicit cleanup for clarity/safety if needed
        # Assuming SQLModel relationships with cascade delete configured or manual cleanup:

        # Delete weeks and workouts explicitly if no cascade on DB level
        # (Though usually `ondelete="CASCADE"` should be in schema)

        # For now, just delete the plan object, assuming cascade works or orphan rows are acceptable temporarily.
        # Ideally, we query and delete children first if we are unsure about DB constraint setup.

        # Manual cascade cleanup to be safe:
        weeks = self.session.exec(
            select(PlanWeek).where(PlanWeek.plan_id == plan.id)
        ).all()
        for week in weeks:
            workouts = self.session.exec(
                select(PlanWorkout).where(PlanWorkout.week_id == week.id)
            ).all()
            for w in workouts:
                self.session.delete(w)
            self.session.delete(week)

        self.session.delete(plan)
        self.session.commit()

    def recalculate_plan_progression(self, user: User) -> None:
        # 1. Load active plan
        weeks_schema = self.get_active_plan(user)
        if not weeks_schema:
            print("No active plan to recalculate.")
            return

        # 2. Determine Current Week
        today = datetime.now()
        start_date = today - timedelta(days=today.weekday())
        current_week_start_str = start_date.strftime("%Y-%m-%d")

        # 3. Find index
        start_index = next(
            (
                i
                for i, w in enumerate(weeks_schema)
                if w.weekStarting == current_week_start_str
            ),
            None,
        )

        if start_index is None:
            # print(f"Current week {current_week_start_str} not found in plan.")
            return

        # 4. Get Baseline (Actuals)
        actual_prev_volume = self._get_last_actual_volume(user, start_date)

        DEFAULT_BASE_VOLUME_KM = 62.0
        current_baseline_vol = 0.0

        if actual_prev_volume > 0:
            current_baseline_vol = actual_prev_volume
        else:
            current_baseline_vol = DEFAULT_BASE_VOLUME_KM * 1000

        # 5. Calculate Progression (Pure Logic)
        plan_logic.calculate_future_progression(
            weeks_schema,
            start_index=start_index,
            initial_baseline_vol=current_baseline_vol,
        )

        # 6. Save
        plan_data = [w.model_dump() for w in weeks_schema]
        self.create_or_update_plan(
            plan_data,
            user=user,
            title=f"Auto-Update {datetime.now().strftime('%Y-%m-%d')}",
            activate=True,
        )
