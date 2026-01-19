import pytest
from unittest.mock import patch
from datetime import date, timedelta
from sqlmodel import Session, select, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from app.services.plans import PlanService
from app.core.database import RunnerPlan, User, PlanWeek
from app.schemas import WorkoutCreate, ActivityType

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@patch("app.services.plans.ValidationEngine")
def test_add_workout_creates_week_if_missing(MockValidationEngine, session: Session):
    # Setup - mock validation to avoid strict rules on empty plan
    mock_instance = MockValidationEngine.return_value
    mock_instance.validate_progression.return_value = []
    mock_instance.validate_structure.return_value = []

    user = User(username="mike", email="mike@test.com")
    session.add(user)
    session.commit()
    
    plan = RunnerPlan(title="Test Plan", is_active=True, user_id=user.id)
    session.add(plan)
    session.commit()
    
    service = PlanService(session)
    
    # Action: Add workout for next Monday
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    
    workout_data = WorkoutCreate(
        date=next_monday,
        name="New Interval Session",
        type=ActivityType.WORKOUT,
        distance_m=5000,
        timeOfDay="AM"
    )
    
    new_workout = service.add_workout(workout_data, username="mike")
    
    # Assert
    assert new_workout.id is not None
    assert new_workout.name == "New Interval Session"
    
    # Check Week was created
    week = session.exec(select(PlanWeek).where(PlanWeek.id == new_workout.week_id)).first()
    assert week is not None
    assert week.plan_id == plan.id
    assert week.start_date == next_monday

def test_add_workout_fails_no_active_plan(session: Session):
    user = User(username="mike", email="mike@test.com")
    session.add(user)
    session.commit()
    
    service = PlanService(session)
    workout_data = WorkoutCreate(
        date=date.today(),
        name="Fail",
        type=ActivityType.RUN
    )
    
    with pytest.raises(ValueError, match="No active plan"):
        service.add_workout(workout_data, username="mike")
