from sqlmodel import Session, select
from app.core.database import User, RunnerProject, RunnerProfile
from datetime import datetime
import json
import os


def migrate_context_json(session: Session, username: str = "mike"):
    """
    Reads data/context.json and populates RunnerProject and RunnerProfile tables.
    """
    if not os.path.exists("data/context.json"):
        print("No context.json found to migrate.")
        return

    with open("data/context.json", "r") as f:
        data = json.load(f)

    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        print(f"User {username} not found, creating...")
        user = User(username=username, email=f"{username}@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

    # 1. Project
    proj_data = data.get("project", {})
    if proj_data:
        # Check if exists
        project = session.exec(
            select(RunnerProject).where(RunnerProject.user_id == user.id)
        ).first()
        if not project:
            event_date = datetime.strptime(
                proj_data.get("eventDate"), "%Y-%m-%d"
            ).date()
            project = RunnerProject(
                user_id=user.id,
                name=proj_data.get("name"),
                goal=proj_data.get("goal"),
                event=proj_data.get("event"),
                event_date=event_date,
            )
            session.add(project)
            print("Created RunnerProject.")

    # 2. Profile
    runner_data = data.get("runner", {})
    if runner_data:
        profile = session.exec(
            select(RunnerProfile).where(RunnerProfile.user_id == user.id)
        ).first()

        if not profile:
            profile = RunnerProfile(
                user_id=user.id,
                age=runner_data.get("age"),
                gender=runner_data.get("gender"),
                height_cm=runner_data.get("height_cm"),
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)
            print("Created RunnerProfile.")

    session.commit()
    print("Context migration complete.")
