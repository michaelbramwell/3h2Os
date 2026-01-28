import sys
import os
from datetime import date

# Add the parent directory to the path so we can import the app
# Use the directory containing 'backend' to allow 'backend.app...' imports if needed
# But standard pattern is usually adding 'backend' to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import Session, engine, RunnerPlan, PlanWeek, PlanWorkout
from app.models.domain import ActivityType


def create_dummy_plan():
    print("Creating dummy plan for deletion testing...")

    with Session(engine) as session:
        # Create a dummy plan
        plan = RunnerPlan(
            title="Temp Plan for Deletion", type="running", is_active=False
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)

        # Add a week
        week = PlanWeek(
            plan_id=plan.id,
            start_date=date.today(),
            week_number=1,  # Note: field might be missing in DB model but let's check schema
            status="normal",
        )
        session.add(week)
        session.commit()
        session.refresh(week)

        # Add a workout
        workout = PlanWorkout(
            week_id=week.id,
            date=date.today(),
            day_name="Mon",
            name="Easy Run",
            description="Just a test run",
            distance_m=5000,
            activity_type=ActivityType.RUN,
            time_of_day="AM",
        )
        session.add(workout)
        session.commit()

        print(f"Successfully created dummy plan with ID: {plan.id}")
        print("You can now refresh the UI and try to delete this plan.")


if __name__ == "__main__":
    create_dummy_plan()
