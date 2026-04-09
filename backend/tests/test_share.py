"""
Tests for the share feature:
  - ShareService.create_share (new, idempotent, wrong user)
  - ShareService.get_activity_by_token (valid, invalid)
  - POST /api/activities/{id}/share endpoint
  - GET /api/share/{token} endpoint (anonymous)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool
from datetime import date

from starlette.requests import Request

from app.main import app
from app.core.database import get_session, User, ActualActivity, ActivityShare
from app.core.auth import verify_jwt_middleware
from app.routers.deps import get_current_user
from app.services.share import ShareService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_user(
    session: Session, username: str = "runner", email: str = "runner@test.com"
) -> User:
    user = User(username=username, email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_activity(
    session: Session, user_id: int, name: str = "Easy run"
) -> ActualActivity:
    activity = ActualActivity(
        user_id=user_id,
        date=date(2026, 1, 15),
        name=name,
        type="running",
        distance_m=10000.0,
        duration_s=3600.0,
        source="garmin",
    )
    session.add(activity)
    session.commit()
    session.refresh(activity)
    return activity


@pytest.fixture(name="client")
def client_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

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

    async def jwt_override(request: Request):
        payload = {
            "sub": "test-user-id",
            "preferred_username": "test_runner",
            "realm_access": {"roles": []},
        }
        request.state.user = payload
        return payload

    app.dependency_overrides[get_session] = get_session_override
    app.dependency_overrides[get_current_user] = get_current_user_override
    app.dependency_overrides[verify_jwt_middleware] = jwt_override

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def _get_test_user(client) -> User:
    """Retrieve the test user that the client fixture creates on first auth call."""
    # Trigger user creation by hitting any auth-required endpoint
    engine = app.dependency_overrides[get_session]().__next__().__class__
    # Simpler: return from the override directly
    override = app.dependency_overrides.get(get_current_user)
    return override() if override else None


# ---------------------------------------------------------------------------
# ShareService unit tests
# ---------------------------------------------------------------------------


class TestShareService:
    def test_create_share_new(self, session):
        """First share call for an activity creates a token."""
        user = _make_user(session)
        activity = _make_activity(session, user.id)

        service = ShareService(session)
        share = service.create_share(activity_id=activity.id, user_id=user.id)

        assert share.id is not None
        assert len(share.token) == 64  # secrets.token_hex(32) produces 64 hex chars
        assert share.activity_id == activity.id

    def test_create_share_idempotent(self, session):
        """Calling create_share twice returns the same token."""
        user = _make_user(session)
        activity = _make_activity(session, user.id)

        service = ShareService(session)
        share1 = service.create_share(activity_id=activity.id, user_id=user.id)
        share2 = service.create_share(activity_id=activity.id, user_id=user.id)

        assert share1.token == share2.token
        assert share1.id == share2.id

    def test_create_share_wrong_user(self, session):
        """create_share raises ValueError when the activity belongs to a different user."""
        owner = _make_user(session, username="owner", email="owner@test.com")
        other = _make_user(session, username="other", email="other@test.com")
        activity = _make_activity(session, owner.id)

        service = ShareService(session)
        with pytest.raises(ValueError):
            service.create_share(activity_id=activity.id, user_id=other.id)

    def test_create_share_nonexistent_activity(self, session):
        """create_share raises ValueError for a non-existent activity id."""
        user = _make_user(session)
        service = ShareService(session)
        with pytest.raises(ValueError):
            service.create_share(activity_id=99999, user_id=user.id)

    def test_get_activity_by_token_valid(self, session):
        """get_activity_by_token returns an ActivitySchema for a valid token."""
        user = _make_user(session)
        activity = _make_activity(session, user.id, name="Long run")

        service = ShareService(session)
        share = service.create_share(activity_id=activity.id, user_id=user.id)

        result = service.get_activity_by_token(share.token)
        assert result is not None
        assert result.name == "Long run"
        assert result.id == activity.id
        assert result.distance_m == 10000.0

    def test_get_activity_by_token_invalid(self, session):
        """get_activity_by_token returns None for an unknown token."""
        service = ShareService(session)
        result = service.get_activity_by_token("nonexistenttoken0000000000000000")
        assert result is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestShareEndpoints:
    def _create_activity_for_test_user(self, client) -> int:
        """
        Helper: post an activity via the actuals endpoint so the test user owns it,
        then return its DB id.
        """
        payload = [
            {
                "date": "2026-02-10",
                "name": "Test long run",
                "type": "running",
                "distance_m": 15000.0,
                "duration_s": 5400.0,
                "source": "garmin",
            }
        ]
        resp = client.post("/api/actuals", json=payload)
        assert resp.status_code == 200

        # Retrieve to get the id
        resp2 = client.get("/api/actuals.json")
        assert resp2.status_code == 200
        activities = resp2.json()
        assert len(activities) >= 1
        # Find by name
        match = next(a for a in activities if a["name"] == "Test long run")
        return match["id"]

    def test_create_share_endpoint(self, client):
        """POST /api/activities/{id}/share returns token and URL."""
        activity_id = self._create_activity_for_test_user(client)
        assert activity_id is not None

        resp = client.post(f"/api/activities/{activity_id}/share")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert "url" in data
        assert f"/share/{data['token']}" in data["url"]
        assert len(data["token"]) == 64

    def test_create_share_endpoint_idempotent(self, client):
        """Calling the share endpoint twice returns the same token."""
        activity_id = self._create_activity_for_test_user(client)

        resp1 = client.post(f"/api/activities/{activity_id}/share")
        resp2 = client.post(f"/api/activities/{activity_id}/share")
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["token"] == resp2.json()["token"]

    def test_create_share_nonexistent_activity(self, client):
        """POST /api/activities/99999/share returns 403."""
        resp = client.post("/api/activities/99999/share")
        assert resp.status_code == 403

    def test_get_shared_activity_valid(self, client):
        """GET /api/share/{token} returns the activity (no auth required)."""
        activity_id = self._create_activity_for_test_user(client)
        share_resp = client.post(f"/api/activities/{activity_id}/share")
        token = share_resp.json()["token"]

        # Fetch without auth headers — TestClient sends no auth by default when
        # we make a raw get (dependency override only applies to get_current_user,
        # not to the anonymous endpoint which skips auth entirely).
        resp = client.get(f"/api/share/{token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Test long run"
        assert data["distance_m"] == 15000.0

    def test_get_shared_activity_invalid_token(self, client):
        """GET /api/share/{bad_token} returns 404."""
        resp = client.get(
            "/api/share/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert resp.status_code == 404
