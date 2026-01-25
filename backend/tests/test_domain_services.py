import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from app.services.plans import PlanService
from app.services.context import ContextService
from app.core.database import User
# Removed unused imports: User, RunnerPlan, PlanWeek, PlanWorkout

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

def test_plan_service_create_and_retrieve(session):
    service = PlanService(session)
    username = "testuser"
    
    # Minimal Valid Plan Data for Relational Mapper
    # Mapper requires 'weekStarting' and valid day dates matching the week
    plan_data = [
        {
            "weekStarting": "2026-01-05", 
            "status": "normal",
            "days": {
                "Mon": {
                    "date": "2026-01-05", 
                    "workouts": [
                        {
                            "name": "5k Recovery",
                            "type": "Easy",
                            "distance_m": 5000,
                            "timeOfDay": "AM"
                        }
                    ]
                }
            }
        }
    ]

    # 1. Create Plan
    user = User(username=username, email="test@example.com")
    session.add(user)
    session.commit()

    new_plan = service.create_or_update_plan(
        plan_data, 
        user=user, 
        title="Test Plan", 
        activate=True
    )

    assert new_plan.title == "Test Plan"
    assert new_plan.is_active is True
    assert new_plan.user_id is not None

    # 2. Retrieve via Service
    # This exercises the fallback logic (Relational -> Blob -> File)
    # Since we just created it with relational data, it should read from relational tables via mappers
    fetched_weeks = service.get_active_plan(user=user)
    
    assert len(fetched_weeks) == 1
    # Check data integrity from DTO
    assert fetched_weeks[0].status == "normal"
    # Note Pydantic v2 might serialize differently, but we check object access
    assert fetched_weeks[0].days["Mon"].workouts[0].name == "5k Recovery"

def test_plan_service_activation_logic(session):
    service = PlanService(session)
    username = "activation_user"
    user = User(username=username, email="activation@test.com")
    session.add(user)
    session.commit()

    plan_1 = [{"week": 1}] # Simplistic data for blob-only test if mapper fails (though mapper might log error and continue)
    
    # Create Plan A (Active)
    p1 = service.create_or_update_plan(plan_1, user=user, title="Plan A", activate=True)
    
    # Create Plan B (Inactive)
    p2 = service.create_or_update_plan(plan_1, user=user, title="Plan B", activate=False)
    
    session.refresh(p1)
    session.refresh(p2)
    assert p1.is_active is True
    assert p2.is_active is False
    
    # Activate Plan B
    service.activate_plan(p2.id)
    
    session.refresh(p1)
    session.refresh(p2)
    assert p1.is_active is False
    assert p2.is_active is True

def test_context_service_defaults(session):
    service = ContextService(session)
    username = "no_context_user"
    user = User(username=username, email="noctx@test.com")
    session.add(user)
    session.commit()
    
    # Service should return empty context when user has no profile/project
    ctx = service.get_context(user=user)
    
    # Assert values are defaults/empty
    assert ctx.runner.age == 0
    assert ctx.project.name == ""
    assert ctx.project.event == ""

