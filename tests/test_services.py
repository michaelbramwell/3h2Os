import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
from app.core.services import save_plan_to_db
from app.core.database import User, RunnerPlan
from unittest.mock import patch

# Create an in-memory database for testing
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

def test_save_plan_to_db_creates_user_and_plan(session):
    plan_data = [{"weekStarting": "2026-01-01", "days": {}}]
    
    # 1. First run, user doesn't exist
    new_plan = save_plan_to_db(plan_data, session, username="testuser")
    
    assert new_plan.title.startswith("Plan Update")
    assert new_plan.is_active is True
    assert new_plan.user_id is not None
    
    user = session.exec(select(User).where(User.username == "testuser")).first()
    assert user is not None
    assert user.email == "testuser@example.com"
    
    plans = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == user.id)).all()
    assert len(plans) == 1
    assert plans[0].is_active is True

def test_save_plan_archives_old_plans(session):
    plan_data_1 = [{"week": 1}]
    plan_data_2 = [{"week": 2}]
    
    # 1. Create first plan
    plan1 = save_plan_to_db(plan_data_1, session, username="testuser")
    
    # 2. Create second plan
    plan2 = save_plan_to_db(plan_data_2, session, username="testuser")
    
    # Refresh objects from session
    session.refresh(plan1)
    session.refresh(plan2)
    
    assert plan1.is_active is False
    assert plan2.is_active is True
