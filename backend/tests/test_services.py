import pytest
from sqlmodel import Session, select
from app.core.services import save_plan_to_db
from app.core.database import User, RunnerPlan, PlanWeek, PlanWorkout


def test_save_plan_to_db_creates_user_and_plan(session):
    # Relational mapper requires 'weekStarting' and valid day dates
    plan_data = [
        {
            "weekStarting": "2026-01-05",
            "status": "normal",
            "days": {
                "Mon": {
                    "date": "2026-01-05",  # Required by mapper
                    "workouts": [
                        {
                            "name": "5k Recovery",
                            "type": "Easy",
                            "distance_m": 5000,
                            "timeOfDay": "AM",
                        }
                    ],
                }
            },
        }
    ]

    # 1. First run, user doesn't exist
    new_plan = save_plan_to_db(plan_data, session, username="testuser", activate=True)

    assert new_plan.title.startswith("Plan Update")
    assert new_plan.is_active is True
    assert new_plan.user_id is not None

    user = session.exec(select(User).where(User.username == "testuser")).first()
    assert user is not None
    assert user.email == "testuser@example.com"

    plans = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == user.id)).all()
    assert len(plans) == 1
    assert plans[0].is_active is True

    # 2. Verify Relational Data Support
    weeks = session.exec(select(PlanWeek).where(PlanWeek.plan_id == new_plan.id)).all()
    assert len(weeks) == 1
    assert weeks[0].start_date.isoformat() == "2026-01-05"
    assert weeks[0].status == "normal"

    workouts = session.exec(
        select(PlanWorkout).where(PlanWorkout.week_id == weeks[0].id)
    ).all()
    assert len(workouts) == 1
    # Check updated mapping: "Easy" -> Type: "Run", Format: "Easy"
    assert workouts[0].activity_type == "Run"
    assert workouts[0].workout_format == "Easy"
    assert workouts[0].distance_m == 5000
    assert workouts[0].date.isoformat() == "2026-01-05"


def test_save_plan_archives_old_plans(session):
    plan_data_1 = [{"week": 1}]
    plan_data_2 = [{"week": 2}]

    # 1. Create first plan
    plan1 = save_plan_to_db(plan_data_1, session, username="testuser")

    # 2. Create second plan
    plan2 = save_plan_to_db(plan_data_2, session, username="testuser", activate=True)

    # Refresh objects from session
    session.refresh(plan1)
    session.refresh(plan2)

    assert plan1.is_active is False
    assert plan2.is_active is True
