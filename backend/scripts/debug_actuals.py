import sys
import os
from sqlmodel import select, Session
from app.core.database import engine, ActualActivity, RunnerPlan, User

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


def debug_db_content():
    with Session(engine) as session:
        # 1. Get default user
        username = "runner"
        user = session.exec(select(User).where(User.username == username)).first()
        if not user:
            print(f"User '{username}' not found!")
            return

        print(f"User: {user.username} (ID: {user.id})")

        # 2. Check Active Plan
        plan = session.exec(
            select(RunnerPlan)
            .where(RunnerPlan.user_id == user.id)
            .where(RunnerPlan.is_active == True)
        ).first()

        if plan:
            print(
                f"Active Plan: ID={plan.id}, Title='{plan.title}', Type='{plan.type}'"
            )
        else:
            print("No Active Plan found for user.")

        # 3. Check Activities and their Types
        activities = session.exec(
            select(ActualActivity.type)
            .where(ActualActivity.user_id == user.id)
            .distinct()
        ).all()

        print("\nDistinct Activity Types in DB for this user:")
        for t in activities:
            print(f" - '{t}'")

        # 4. Count Total Activities
        count = session.exec(
            select(ActualActivity).where(ActualActivity.user_id == user.id)
        ).all()
        print(f"\nTotal Activities: {len(count)}")


if __name__ == "__main__":
    debug_db_content()
