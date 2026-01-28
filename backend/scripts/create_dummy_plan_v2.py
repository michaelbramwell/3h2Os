import sys
import os
from datetime import date

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import Session, engine, RunnerPlan, PlanWeek, PlanWorkout, User
from sqlmodel import select


def create_dummy_plan():
    print("Creating dummy plan for deletion testing...")

    with Session(engine) as session:
        # Get or create the default user "runner"
        username = "runner"
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            print("User 'runner' not found. Creating...")
            user = User(username=username, email="runner@example.com")
            session.add(user)
            session.commit()
            session.refresh(user)

        print(f"Assigning plan to user: {user.username} (ID: {user.id})")

        # Create a dummy plan linked to the user
        plan = RunnerPlan(
            title="Temp Plan for Deletion",
            type="running",
            is_active=False,
            user_id=user.id,  # Explicitly link to user
        )
        session.add(plan)
        session.commit()
        session.refresh(plan)

        # Add a week
        week = PlanWeek(
            plan_id=plan.id, start_date=date.today(), week_number=1, status="normal"
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
            # activity_type="run", # Using string literal if enum import fails, or ActivityType.RUN
            time_of_day="AM",
        )
        session.add(workout)
        session.commit()

        print(f"Successfully created dummy plan with ID: {plan.id}")
        print("You can now refresh the UI and try to delete this plan.")


if __name__ == "__main__":
    create_dummy_plan()
