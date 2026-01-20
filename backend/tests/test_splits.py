import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from datetime import date
from app.services.activities import ActivityService
from app.schemas import ActivitySchema, HrZone
from app.core.database import User

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

def test_save_and_retrieve_activity_with_splits(session):
    # Setup User
    user = User(username="runner", email="test@test.com")
    session.add(user)
    session.commit()
    
    service = ActivityService(session)
    
    # Create Activity with Splits
    splits_data = [
        {"distance": 1000, "averageSpeed": 3.5, "averageHR": 140},
        {"distance": 1000, "averageSpeed": 3.6, "averageHR": 145}
    ]
    
    activity = ActivitySchema(
        date="2026-01-20",
        name="Intervals",
        type="Run",
        distance_m=2000,
        duration_s=600,
        activityId=12345,
        average_pace_m_s=3.55,
        splits=splits_data
    )
    
    # Save
    service.save_activities([activity], user=user)
    
    # Retrieve
    activities = service.get_activities(user=user)
    assert len(activities) == 1
    saved_activity = activities[0]
    
    assert saved_activity.activityId == 12345
    assert saved_activity.splits is not None
    assert len(saved_activity.splits) == 2
    assert saved_activity.splits[0]["distance"] == 1000
    assert saved_activity.splits[1]["averageHR"] == 145
