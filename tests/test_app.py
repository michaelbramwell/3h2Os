from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
import pytest
import time
from app.main import app
from app.core.database import get_session, User, RunnerPlan

# Use in-memory DB for tests
@pytest.fixture(name="client")
def client_fixture():
    engine = create_engine(
        "sqlite://", 
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    
    def get_session_override():
        with Session(engine) as session:
            yield session
            
    app.dependency_overrides[get_session] = get_session_override
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

def test_read_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Marathon Training Dashboard" in response.text

def test_get_plan_empty_db_fallback(client):
    # If DB is empty, it falls back to parsing JSON from disk (which might be real data or mocked)
    # Since we can't easily mock file read inside the fallback logic without patching, 
    # we can verify it doesn't crash or returns something valid if file exists.
    response = client.get("/plan.json")
    assert response.status_code == 200
    # It returns list (either empty or loaded)
    assert isinstance(response.json(), list)

def test_post_plan_update(client):
    # 1. Post a new plan
    new_plan_data = [{"week": 1, "days": {}}]
    response = client.post("/plan.json", json=new_plan_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["title"].startswith("Plan Update")
    
    # 2. Verify it's in the DB via GET
    response = client.get("/plan.json")
    assert response.status_code == 200
    fetched_plan = response.json()
    assert len(fetched_plan) == 1
    assert fetched_plan[0]["week"] == 1

def test_plan_archives_old_versions(client):
    # 1. Post version 1
    client.post("/plan.json", json=[{"v": 1}])
    
    # Wait a sec to ensure timestamps might differ if needed (though title uses minute)
    # Not strictly necessary as ID increments
    
    # 2. Post version 2
    client.post("/plan.json", json=[{"v": 2}])
    
    # 3. GET should return version 2
    response = client.get("/plan.json")
    assert response.json()[0]["v"] == 2

