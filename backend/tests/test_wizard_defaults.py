"""
Tests for GET /api/wizard/defaults endpoint.
"""

import json
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session, User, RunnerProfile, ActualActivity
from app.routers.deps import get_current_user
from app.core.auth import verify_jwt_middleware
from fastapi import Request


@pytest.fixture(name="client_with_profile")
def client_with_profile_fixture():
    """
    TestClient backed by an in-memory DB that has a User + RunnerProfile pre-seeded.
    Yields (client, engine) so tests can insert extra rows.
    """
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    app.state.test_engine = engine

    # Seed user + profile
    with Session(engine) as seed_session:
        user = User(username="test_wizard", email="wizard@test.com")
        seed_session.add(user)
        seed_session.commit()
        seed_session.refresh(user)

        profile = RunnerProfile(
            user_id=user.id,
            age=32,
            gender="male",
            height_cm=178,
            weight_kg=73.5,
            experience_level="intermediate",
            weekly_availability=5,
            longest_recent_distance_m=18000,
            pain_points_json=json.dumps(["pacing", "injury"]),
        )
        seed_session.add(profile)
        seed_session.commit()

    def get_session_override():
        with Session(engine) as s:
            yield s

    def get_current_user_override():
        with Session(engine) as s:
            return s.exec(select(User).where(User.username == "test_wizard")).first()

    async def verify_jwt_override(request: Request):
        return {"sub": "test-wiz", "preferred_username": "test_wizard"}

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[verify_jwt_middleware] = verify_jwt_override

    with TestClient(app) as client:
        yield client, engine

    app.dependency_overrides.clear()
    if hasattr(app.state, "test_engine"):
        del app.state.test_engine


@pytest.fixture(name="client_no_profile")
def client_no_profile_fixture():
    """TestClient with a user but no RunnerProfile."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    app.state.test_engine = engine

    with Session(engine) as seed_session:
        user = User(username="test_noprofile", email="noprofile@test.com")
        seed_session.add(user)
        seed_session.commit()

    def get_session_override():
        with Session(engine) as s:
            yield s

    def get_current_user_override():
        with Session(engine) as s:
            return s.exec(select(User).where(User.username == "test_noprofile")).first()

    async def verify_jwt_override(request: Request):
        return {"sub": "test-noprofile", "preferred_username": "test_noprofile"}

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[verify_jwt_middleware] = verify_jwt_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    if hasattr(app.state, "test_engine"):
        del app.state.test_engine


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_wizard_defaults_returns_200(client_with_profile):
    client, _ = client_with_profile
    response = client.get("/api/wizard/defaults")
    assert response.status_code == 200


def test_wizard_defaults_has_expected_shape(client_with_profile):
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    assert "athlete_profile" in data
    assert "goals_focus" in data


def test_wizard_defaults_age_from_stored_age(client_with_profile):
    """When no birthday is set, age should come from profile.age."""
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    assert data["athlete_profile"]["age"] == 32


def test_wizard_defaults_age_from_birthday(client_with_profile):
    """When birthday is set, age should be computed dynamically."""
    client, engine = client_with_profile
    with Session(engine) as s:
        profile = s.exec(
            select(RunnerProfile).where(RunnerProfile.user_id != None)
        ).first()
        # Set birthday to 30 years ago today
        today = date.today()
        bday = date(today.year - 30, today.month, today.day)
        profile.birthday = bday
        s.add(profile)
        s.commit()

    data = client.get("/api/wizard/defaults").json()
    assert data["athlete_profile"]["age"] == 30


def test_wizard_defaults_weight_kg(client_with_profile):
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    assert data["athlete_profile"]["weight_kg"] == pytest.approx(73.5)


def test_wizard_defaults_experience_level(client_with_profile):
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    assert data["athlete_profile"]["experience_level"] == "intermediate"


def test_wizard_defaults_weekly_availability(client_with_profile):
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    assert data["goals_focus"]["weekly_availability"] == 5


def test_wizard_defaults_longest_recent_distance_from_profile(client_with_profile):
    """When longest_recent_distance_m is stored on profile, return it directly."""
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    assert data["goals_focus"]["longest_recent_distance_m"] == 18000


def test_wizard_defaults_longest_recent_distance_from_activities(client_with_profile):
    """When profile has no stored value, compute from recent running activities."""
    client, engine = client_with_profile
    # Clear the stored value
    with Session(engine) as s:
        profile = s.exec(
            select(RunnerProfile).where(RunnerProfile.user_id != None)
        ).first()
        profile.longest_recent_distance_m = None
        s.add(profile)
        s.commit()
        # Insert a recent running activity with known distance
        user = s.exec(select(User).where(User.username == "test_wizard")).first()
        activity = ActualActivity(
            user_id=user.id,
            date=date.today(),
            name="Morning Run",
            type="running",
            distance_m=22000.0,
            duration_s=7200.0,
            source="garmin",
        )
        s.add(activity)
        s.commit()

    data = client.get("/api/wizard/defaults").json()
    assert data["goals_focus"]["longest_recent_distance_m"] == 22000


def test_wizard_defaults_pain_points(client_with_profile):
    client, _ = client_with_profile
    data = client.get("/api/wizard/defaults").json()
    pain_points = data["goals_focus"]["pain_points"]
    assert "pacing" in pain_points
    assert "injury" in pain_points


def test_wizard_defaults_hr_zones_from_training_zones_json(client_with_profile):
    """When training_zones_json has HR zones, custom_zones should be returned."""
    client, engine = client_with_profile
    hr_zones = [
        {"zone": 1, "name": "Z1", "minBpm": 100, "maxBpm": 130},
        {"zone": 2, "name": "Z2", "minBpm": 130, "maxBpm": 150},
    ]
    with Session(engine) as s:
        profile = s.exec(
            select(RunnerProfile).where(RunnerProfile.user_id != None)
        ).first()
        profile.training_zones_json = json.dumps({"hr": hr_zones})
        s.add(profile)
        s.commit()

    data = client.get("/api/wizard/defaults").json()
    assert data["athlete_profile"]["use_calculated_zones"] is False
    assert data["athlete_profile"]["custom_zones"]["heartRate"] == hr_zones


def test_wizard_defaults_no_profile_returns_empty_defaults(client_no_profile):
    """When there is no RunnerProfile, the endpoint should still return 200 with nulls."""
    data = client_no_profile.get("/api/wizard/defaults").json()
    assert data["athlete_profile"]["age"] is None
    assert data["goals_focus"]["weekly_availability"] is None
