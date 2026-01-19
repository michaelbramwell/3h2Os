import pytest
from datetime import date, timedelta
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.services.plans import PlanService
from app.core.database import User, RunnerPlan, PlanWeek, PlanWorkout

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

def test_delete_future_workout(session):
    user, plan = create_test_data(session)
    future_date = date.today() + timedelta(days=5)
    
    week = PlanWeek(plan_id=plan.id, start_date=future_date, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)
    
    workout = PlanWorkout(
        week_id=week.id, date=future_date, 
        name="Future Run", day_name="Mon", 
        activity_type="Run", distance_m=5000, 
        time_of_day="AM"
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)
    
    service = PlanService(session)
    service.delete_workout(workout.id)
    
    deleted = session.get(PlanWorkout, workout.id)
    assert deleted is None

def test_prevent_delete_past_workout(session):
    user, plan = create_test_data(session)
    past_date = date.today() - timedelta(days=5)
    
    week = PlanWeek(plan_id=plan.id, start_date=past_date, status="normal")
    session.add(week)
    session.commit()
    session.refresh(week)
    
    workout = PlanWorkout(
        week_id=week.id, date=past_date, 
        name="Past Run", day_name="Mon", 
        activity_type="Run", distance_m=5000
    )
    session.add(workout)
    session.commit()
    session.refresh(workout)
    
    service = PlanService(session)
    
    with pytest.raises(ValueError, match="already occurred"):
        service.delete_workout(workout.id)
