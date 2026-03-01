from sqlmodel import Session, select, text
from app.core.database import User, RunnerProject, RunnerProfile, FeatureFlag
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


def migrate_add_user_types_column(session: Session):
    """
    Adds the user_types_json column to the user table if it doesn't exist.
    Safe to run repeatedly (idempotent).
    """
    try:
        session.exec(text('SELECT user_types_json FROM "user" LIMIT 1'))
        print("user.user_types_json column already exists, skipping.")
    except Exception:
        session.rollback()
        try:
            session.exec(
                text(
                    'ALTER TABLE "user" ADD COLUMN user_types_json VARCHAR DEFAULT \'["standard"]\''
                )
            )
            session.commit()
            print("Added user.user_types_json column.")
        except Exception as e:
            session.rollback()
            print(f"Could not add user_types_json column: {e}")


def create_feature_flag_table(session: Session):
    """
    Creates the featureflag table if it doesn't already exist.
    Safe to run repeatedly (idempotent).
    """
    try:
        session.exec(text("SELECT id FROM featureflag LIMIT 1"))
        print("featureflag table already exists, skipping creation.")
    except Exception:
        session.rollback()
        try:
            session.exec(
                text("""
                CREATE TABLE IF NOT EXISTS featureflag (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR NOT NULL UNIQUE,
                    enabled_for_json VARCHAR NOT NULL DEFAULT '[]',
                    description VARCHAR
                )
            """)
            )
            session.commit()
            print("Created featureflag table.")
        except Exception as e:
            session.rollback()
            print(f"Could not create featureflag table: {e}")


def seed_feature_flags(session: Session):
    """
    Ensures the core feature flags exist with their default values.
    Only inserts flags that are missing; never overwrites existing ones.
    """
    defaults = [
        {
            "name": "isSwimmingEnabled",
            "enabled_for_json": "[]",  # off for all users
            "description": "Controls visibility of swimming plans and UI across the app.",
        },
    ]

    for flag_def in defaults:
        existing = session.exec(
            select(FeatureFlag).where(FeatureFlag.name == flag_def["name"])
        ).first()
        if not existing:
            flag = FeatureFlag(**flag_def)
            session.add(flag)
            print(f"Seeded feature flag: {flag_def['name']}")

    session.commit()
    print("Feature flag seeding complete.")
