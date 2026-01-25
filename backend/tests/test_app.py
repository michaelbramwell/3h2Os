from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
import pytest
from app.main import app
from app.core.database import get_session, RunnerPlan, User
from app.routers.api import get_current_user
from app.core.auth import verify_jwt_middleware
from fastapi import Request


# Use in-memory DB for tests
@pytest.fixture(name="client")
def client_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    # Store engine ref so we can create sessions inside tests if needed
    app.state.test_engine = engine

    def get_session_override():
        with Session(engine) as session:
            yield session

    def get_current_user_override():
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.username == "test_runner")
            ).first()
            if not user:
                user = User(username="test_runner", email="test@runner.com")
                session.add(user)
                session.commit()
                session.refresh(user)
            return user

    async def verify_jwt_middleware_override(request: Request):
        # Bypass auth for tests - return a mock payload if needed by endpoints
        return {
            "sub": "test-user-id",
            "preferred_username": "test_runner",
            "email": "test@runner.com",
        }

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[verify_jwt_middleware] = verify_jwt_middleware_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    if hasattr(app.state, "test_engine"):
        del app.state.test_engine


def test_read_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Marathon Training Dashboard" in response.text


def test_get_plan_empty_db_fallback(client):
    # If DB is empty, it falls back to parsing JSON from disk (which might be real data or mocked)
    # Since we can't easily mock file read inside the fallback logic without patching,
    # we can verify it doesn't crash or returns something valid if file exists.
    response = client.get("/api/plan.json")
    assert response.status_code == 200
    # It returns list (either empty or loaded)
    assert isinstance(response.json(), list)


def test_post_plan_update(client):
    # 1. Post a new plan
    new_plan_data = [{"weekStarting": "2026-01-01", "days": {}}]
    response = client.post("/api/plan.json", json=new_plan_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["title"].startswith("Plan Update")

    # 2. Verify it's in the DB via GET
    response = client.get("/api/plan.json")
    assert response.status_code == 200
    fetched_plan = response.json()
    assert len(fetched_plan) == 1
    assert fetched_plan[0]["weekStarting"] == "2026-01-01"


def test_plan_archives_old_versions(client):
    # 1. Post version 1
    client.post("/api/plan.json", json=[{"weekStarting": "2026-01-01", "status": "v1"}])

    # Wait a sec to ensure timestamps might differ if needed (though title uses minute)
    # Not strictly necessary as ID increments

    # 2. Post version 2
    client.post("/api/plan.json", json=[{"weekStarting": "2026-01-01", "status": "v2"}])

    # 3. GET should return version 2
    response = client.get("/api/plan.json")
    assert response.json()[0]["status"] == "v2"


def test_get_plan_uses_relational_data(client):
    # 1. Post a plan with recognizable structure
    plan_data = [
        {
            "weekStarting": "2026-02-01",
            "status": "normal",
            "days": {
                "Mon": {
                    "date": "2026-02-01",
                    "workouts": [
                        {
                            "name": "Relational Check",
                            "type": "Easy",
                            "distance_m": 8000,
                            "timeOfDay": "AM",
                        }
                    ],
                }
            },
        }
    ]
    client.post("/api/plan.json", json=plan_data)

    # 2. Verify normal fetch works first
    response = client.get("/api/plan.json")
    assert response.status_code == 200
    assert response.json()[0]["weekStarting"] == "2026-02-01"

    # 3. Sabotage the JSON blob in the DB to prove we read from Relational tables
    # using the engine we stored in app.state
    with Session(app.state.test_engine) as session:
        # User is created by the POST logic in save_plan_to_db -> username="test_runner" (override)
        user = session.exec(select(User).where(User.username == "test_runner")).first()
        plan = session.exec(
            select(RunnerPlan)
            .where(RunnerPlan.user_id == user.id)
            .where(RunnerPlan.is_active == True)
        ).first()
        # Corrupt/Clear the blob
        plan.plan_json = "[]"
        session.add(plan)
        session.commit()

    # 4. Fetch again - should still work because of Relational Data
    response = client.get("/api/plan.json")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["weekStarting"] == "2026-02-01"
    assert data[0]["days"]["Mon"]["workouts"][0]["name"] == "Relational Check"
    assert data[0]["days"]["Mon"]["workouts"][0]["distance_m"] == 8000


def test_create_plan_v2_endpoint(client):
    # Setup: Create an initial active plan
    client.post("/api/plan.json", json=[{"weekStarting": "2026-02-01", "days": {}}])

    # Test the new /plans endpoint with the required schema
    payload = {
        "title": "New V2 Plan",
        "weeks": [
            {
                "weekStarting": "2026-03-01",
                "days": {"Mon": {"date": "2026-03-01", "workouts": []}},
            }
        ],
    }
    response = client.post("/api/plans", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["title"] == "New V2 Plan"
    new_id = data["id"]

    # Verify the OLD plan is still active (2026-02-01)
    response = client.get("/api/plan.json")
    fetched = response.json()
    assert fetched[0]["weekStarting"] == "2026-02-01"

    # Activate the new plan
    response = client.put(f"/api/plans/{new_id}/activate")
    assert response.status_code == 200

    # Verify the NEW plan is now active
    response = client.get("/api/plan.json")
    fetched = response.json()
    assert fetched[0]["weekStarting"] == "2026-03-01"
