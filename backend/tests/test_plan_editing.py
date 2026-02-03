import pytest
from unittest.mock import patch
from datetime import date, timedelta
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.services.plans import PlanService
from app.core.database import User, RunnerPlan, PlanWeek, PlanWorkout, ActualActivity
from app.schemas import WorkoutUpdate
from app.models.domain import ActivityType


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def create_test_data(session: Session):
    user = User(username="testrunner", email="test@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    plan = RunnerPlan(title="Test Plan", user_id=user.id, is_active=True)
    session.add(plan)
    session.commit()
    session.refresh(plan)

    return user, plan


@patch("app.services.plans.ValidationEngine")
def test_update_future_workout(MockValidationEngine, session):
    # Mock validation
    MockValidationEngine.return_value.validate_progression.return_value = []
    MockValidationEngine.return_value.validate_structure.return_value = []

    user, plan = create_test_data(session)
    future_date = date.today() + timedelta(days=5)

    week = PlanWeek(plan_id=plan.id, start_date=future_date, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)

    workout = PlanWorkout(
        week_id=week.id,
        date=future_date,
        name="Future Run",
        day_name="Mon",
        activity_type=ActivityType.RUN,
        distance_m=5000,
        time_of_day="AM",
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)

    service = PlanService(session)
    update = WorkoutUpdate(name="Updated Run", timeOfDay="PM")

    updated = service.update_workout(workout.id, update)

    assert updated.name == "Updated Run"
    assert updated.time_of_day == "PM"


def test_prevent_update_past_workout(session):
    user, plan = create_test_data(session)
    past_date = date.today() - timedelta(days=5)

    week = PlanWeek(plan_id=plan.id, start_date=past_date, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)

    workout = PlanWorkout(
        week_id=week.id,
        date=past_date,
        name="Past Run",
        day_name="Mon",
        activity_type=ActivityType.RUN,
        distance_m=5000,
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)

    service = PlanService(session)
    update = WorkoutUpdate(name="Cheating Past")

    with pytest.raises(ValueError, match="already occurred"):
        service.update_workout(workout.id, update)


@patch("app.services.plans.ValidationEngine")
def test_prevent_update_today_workout_if_completed(MockValidationEngine, session):
    # Mock validation to reach "Activity logged" check
    MockValidationEngine.return_value.validate_progression.return_value = []
    MockValidationEngine.return_value.validate_structure.return_value = []

    user, plan = create_test_data(session)
    today = date.today()

    week = PlanWeek(plan_id=plan.id, start_date=today, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)

    workout = PlanWorkout(
        week_id=week.id,
        date=today,
        name="Today Run",
        day_name="Mon",
        activity_type=ActivityType.RUN,
        distance_m=5000,
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)

    # Add an actual activity for today
    actual = ActualActivity(
        activity_id=12345,
        user_id=user.id,
        date=today,
        name="Morning Run",
        type="running",
        distance_m=5000,
        duration_s=1800,
    )
    session.add(actual)
    session.commit()
    session.refresh(actual)  # Ensure ID and relationships

    service = PlanService(session)
    update = WorkoutUpdate(name="Trying to change after done")

    with pytest.raises(ValueError, match="Activity logged"):
        service.update_workout(workout.id, update)


@patch("app.services.plans.ValidationEngine")
def test_allow_update_today_workout_if_not_completed(MockValidationEngine, session):
    # Mock validation
    MockValidationEngine.return_value.validate_progression.return_value = []
    MockValidationEngine.return_value.validate_structure.return_value = []

    user, plan = create_test_data(session)
    today = date.today()

    week = PlanWeek(plan_id=plan.id, start_date=today, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)

    workout = PlanWorkout(
        week_id=week.id,
        date=today,
        name="Today Pending Run",
        day_name="Mon",
        activity_type=ActivityType.RUN,
        distance_m=5000,
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)

    # NO actual activity

    service = PlanService(session)
    update = WorkoutUpdate(name="Changing Plans Before Run")

    updated = service.update_workout(workout.id, update)
    assert updated.name == "Changing Plans Before Run"


def test_update_week_status(session):
    user, plan = create_test_data(session)
    # Create a future week
    start_date = date.today() + timedelta(days=7)
    week = PlanWeek(plan_id=plan.id, start_date=start_date, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)

    service = PlanService(session)
    from app.schemas import WeekUpdate

    # Update to 'recovery'
    update = WeekUpdate(status="recovery")
    updated_week = service.update_week(week.id, update)
    assert updated_week.status == "recovery"
    assert updated_week.id == week.id

    # Verify persistence
    session.refresh(week)
    assert week.status == "recovery"


def test_update_week_not_found(session):
    service = PlanService(session)
    from app.schemas import WeekUpdate

    update = WeekUpdate(status="taper")
    # Assuming ID 999999 doesn't exist
    with pytest.raises(ValueError, match="not found"):
        service.update_week(999999, update)
