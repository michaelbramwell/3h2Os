"""
HTTP integration tests for:
  - require_role auth dependency (401/403 enforcement)
  - GET /api/flags  (user-facing flag resolution)
  - GET /api/admin/flags  (admin listing)
  - PUT /api/admin/flags/{name}  (admin upsert)
  - Swimming guard 403 on wizard endpoints
"""

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_session, User, FeatureFlag
from app.routers.deps import get_current_user
from app.core.auth import verify_jwt_middleware
from fastapi import Request


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _session_override(engine):
    def _get():
        with Session(engine) as s:
            yield s

    return _get


def _user_override(engine, username="test_runner", user_types=None):
    """
    Returns a get_current_user override.  User is created on first call and
    cached so that subsequent _set_user_types calls on the same engine are
    visible to following requests.
    """
    types = user_types if user_types is not None else ["standard"]

    def _get():
        with Session(engine) as s:
            user = s.exec(select(User).where(User.username == username)).first()
            if not user:
                user = User(
                    username=username,
                    email=f"{username}@example.com",
                    user_types_json=json.dumps(types),
                )
                s.add(user)
                s.commit()
                s.refresh(user)
            return user

    return _get


def _seed_flag(engine, name, enabled_for, description=None):
    with Session(engine) as s:
        existing = s.exec(select(FeatureFlag).where(FeatureFlag.name == name)).first()
        if existing:
            existing.enabled_for_json = json.dumps(enabled_for)
            if description is not None:
                existing.description = description
            s.add(existing)
        else:
            flag = FeatureFlag(
                name=name,
                enabled_for_json=json.dumps(enabled_for),
                description=description,
            )
            s.add(flag)
        s.commit()


def _set_user_types(engine, username, types):
    with Session(engine) as s:
        user = s.exec(select(User).where(User.username == username)).first()
        if user:
            user.user_types_json = json.dumps(types)
            s.add(user)
            s.commit()


def _make_jwt_override(roles=None, username="test_runner"):
    """Returns an async dependency that sets request.state.user."""
    realm_roles = roles if roles is not None else []

    async def _jwt(request: Request):
        payload = {
            "sub": "test-user-id",
            "preferred_username": username,
            "realm_access": {"roles": realm_roles},
        }
        request.state.user = payload
        return payload

    return _jwt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """Standard user client — no JWT roles, standard user type."""
    engine = _make_engine()
    app.dependency_overrides[get_session] = _session_override(engine)
    app.dependency_overrides[get_current_user] = _user_override(engine)
    app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override()

    with TestClient(app) as c:
        yield c, engine

    app.dependency_overrides.clear()


@pytest.fixture()
def admin_client():
    """Client whose JWT contains the app_admin realm role."""
    engine = _make_engine()
    app.dependency_overrides[get_session] = _session_override(engine)
    app.dependency_overrides[get_current_user] = _user_override(
        engine, username="admin_user"
    )
    app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override(
        roles=["app_admin"], username="admin_user"
    )

    with TestClient(app) as c:
        yield c, engine

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# require_role enforcement
# ---------------------------------------------------------------------------


class TestRequireRole:
    def test_admin_list_flags_blocked_for_non_admin(self):
        """GET /api/admin/flags must return 403 when the caller lacks app_admin role."""
        engine = _make_engine()
        app.dependency_overrides[get_session] = _session_override(engine)
        app.dependency_overrides[get_current_user] = _user_override(
            engine, username="plain_user"
        )
        app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override(
            roles=["some_other_role"], username="plain_user"
        )

        with TestClient(app) as c:
            response = c.get("/api/admin/flags")

        app.dependency_overrides.clear()
        assert response.status_code == 403
        assert "app_admin" in response.json()["detail"]

    def test_admin_put_flag_blocked_for_non_admin(self):
        """PUT /api/admin/flags/{name} returns 403 for a non-admin."""
        engine = _make_engine()
        app.dependency_overrides[get_session] = _session_override(engine)
        app.dependency_overrides[get_current_user] = _user_override(
            engine, username="plain_user"
        )
        app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override(
            roles=[], username="plain_user"
        )

        with TestClient(app) as c:
            response = c.put(
                "/api/admin/flags/isSwimmingEnabled",
                json={"enabled_for": ["*"]},
            )

        app.dependency_overrides.clear()
        assert response.status_code == 403

    def test_admin_endpoint_allowed_with_app_admin_role(self):
        """GET /api/admin/flags returns 200 when JWT contains app_admin role."""
        engine = _make_engine()
        _seed_flag(engine, "isSwimmingEnabled", [])
        app.dependency_overrides[get_session] = _session_override(engine)
        app.dependency_overrides[get_current_user] = _user_override(
            engine, username="admin_user"
        )
        app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override(
            roles=["app_admin"], username="admin_user"
        )

        with TestClient(app) as c:
            response = c.get("/api/admin/flags")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        names = [f["name"] for f in response.json()]
        assert "isSwimmingEnabled" in names

    def test_user_flags_endpoint_accessible_without_admin_role(self, client):
        """GET /api/flags is accessible to any authenticated user."""
        c, _ = client
        response = c.get("/api/flags")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/flags
# ---------------------------------------------------------------------------


class TestGetFlags:
    def test_empty_db_returns_empty_flags(self, client):
        c, engine = client
        # The startup seeder inserts isSwimmingEnabled; clear it so we get a
        # clean empty state to test the "no flags" path.
        with Session(engine) as s:
            s.exec(select(FeatureFlag))  # ensure table exists
            for flag in s.exec(select(FeatureFlag)).all():
                s.delete(flag)
            s.commit()

        response = c.get("/api/flags")
        assert response.status_code == 200
        assert response.json() == {"flags": {}}

    def test_returns_resolved_booleans_for_standard_user(self, client):
        c, engine = client
        _seed_flag(engine, "isSwimmingEnabled", [])
        _seed_flag(engine, "globalFeature", ["*"])

        response = c.get("/api/flags")
        assert response.status_code == 200
        flags = response.json()["flags"]
        assert flags["isSwimmingEnabled"] is False
        assert flags["globalFeature"] is True

    def test_alpha_user_sees_alpha_flag_enabled(self):
        """User with alpha type sees alpha-gated flag as True."""
        engine = _make_engine()
        _seed_flag(engine, "isSwimmingEnabled", ["alpha"])

        # Create the user directly in the DB with alpha type before the client starts.
        with Session(engine) as s:
            user = User(
                username="alpha_tester",
                email="alpha@example.com",
                user_types_json=json.dumps(["alpha"]),
            )
            s.add(user)
            s.commit()

        app.dependency_overrides[get_session] = _session_override(engine)
        app.dependency_overrides[get_current_user] = _user_override(
            engine, username="alpha_tester", user_types=["alpha"]
        )
        app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override(
            username="alpha_tester"
        )

        with TestClient(app) as c:
            response = c.get("/api/flags")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        assert response.json()["flags"]["isSwimmingEnabled"] is True

    def test_standard_user_does_not_see_alpha_flag(self, client):
        c, engine = client
        _seed_flag(engine, "isSwimmingEnabled", ["alpha"])

        response = c.get("/api/flags")
        assert response.status_code == 200
        assert response.json()["flags"]["isSwimmingEnabled"] is False

    def test_wildcard_flag_enabled_for_all(self, client):
        c, engine = client
        _seed_flag(engine, "isSwimmingEnabled", ["*"])

        response = c.get("/api/flags")
        assert response.status_code == 200
        assert response.json()["flags"]["isSwimmingEnabled"] is True

    def test_multiple_flags_all_resolved(self, client):
        c, engine = client
        _seed_flag(engine, "featureA", ["*"])
        _seed_flag(engine, "featureB", ["beta"])
        _seed_flag(engine, "featureC", [])

        response = c.get("/api/flags")
        assert response.status_code == 200
        flags = response.json()["flags"]
        assert flags["featureA"] is True
        assert flags["featureB"] is False
        assert flags["featureC"] is False


# ---------------------------------------------------------------------------
# GET /api/admin/flags
# ---------------------------------------------------------------------------


class TestAdminListFlags:
    def test_returns_all_flags_with_enabled_for(self, admin_client):
        c, engine = admin_client
        _seed_flag(engine, "betaFeature", ["beta"])

        response = c.get("/api/admin/flags")
        assert response.status_code == 200
        names = {f["name"] for f in response.json()}
        # betaFeature was explicitly seeded; isSwimmingEnabled seeded by startup
        assert "betaFeature" in names

    def test_flag_schema_shape(self, admin_client):
        c, engine = admin_client
        _seed_flag(engine, "testFlag", ["*"], description="all users")

        response = c.get("/api/admin/flags")
        assert response.status_code == 200
        # Find the testFlag entry
        flag = next(f for f in response.json() if f["name"] == "testFlag")
        assert "id" in flag
        assert "name" in flag
        assert "enabled_for" in flag
        assert "description" in flag
        assert isinstance(flag["enabled_for"], list)

    def test_empty_flags_after_clearing(self, admin_client):
        c, engine = admin_client
        # Remove all flags so we can verify an empty list
        with Session(engine) as s:
            for flag in s.exec(select(FeatureFlag)).all():
                s.delete(flag)
            s.commit()

        response = c.get("/api/admin/flags")
        assert response.status_code == 200
        assert response.json() == []


# ---------------------------------------------------------------------------
# PUT /api/admin/flags/{name}
# ---------------------------------------------------------------------------


class TestAdminSetFlag:
    def test_create_new_flag(self, admin_client):
        c, _ = admin_client

        response = c.put(
            "/api/admin/flags/newFeature",
            json={"enabled_for": ["alpha"], "description": "alpha only"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "newFeature"
        assert data["enabled_for"] == ["alpha"]
        assert data["description"] == "alpha only"

    def test_update_existing_flag(self, admin_client):
        c, engine = admin_client
        _seed_flag(engine, "isSwimmingEnabled", [])

        response = c.put(
            "/api/admin/flags/isSwimmingEnabled",
            json={"enabled_for": ["*"]},
        )
        assert response.status_code == 200
        assert response.json()["enabled_for"] == ["*"]

    def test_enable_for_all_then_disable(self, admin_client):
        c, _ = admin_client

        c.put("/api/admin/flags/myFlag", json={"enabled_for": ["*"]})
        response = c.put("/api/admin/flags/myFlag", json={"enabled_for": []})
        assert response.status_code == 200
        assert response.json()["enabled_for"] == []

    def test_description_optional(self, admin_client):
        c, _ = admin_client

        response = c.put(
            "/api/admin/flags/noDesc",
            json={"enabled_for": ["beta"]},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "noDesc"

    def test_roundtrip_visible_in_list(self, admin_client):
        """After a PUT, the new flag appears in GET /api/admin/flags."""
        c, _ = admin_client

        c.put("/api/admin/flags/roundtripFlag", json={"enabled_for": ["premium"]})
        list_response = c.get("/api/admin/flags")
        assert list_response.status_code == 200
        names = [f["name"] for f in list_response.json()]
        assert "roundtripFlag" in names


# ---------------------------------------------------------------------------
# Swimming guard on wizard endpoints
# ---------------------------------------------------------------------------


def _swimming_wizard_payload():
    """Minimal valid WizardInput with swimming sport."""
    return {
        "sport_event": {
            "plan_name": "Test Swim Plan",
            "sport": "swimming",
            "event_type": "pool_1500m",
        },
        "athlete_profile": {
            "experience_level": "beginner",
            "age": 30,
            "weight_kg": 75.0,
        },
        "goals_focus": {
            "primary_goal": "finish",
            "weekly_availability": 4,
            "longest_recent_distance_m": 1500,
        },
        "plan_config": {
            "total_weeks": 12,
        },
    }


def _running_wizard_payload():
    """Minimal valid WizardInput with running sport."""
    return {
        "sport_event": {
            "plan_name": "Marathon Plan",
            "sport": "running",
            "event_type": "marathon",
        },
        "athlete_profile": {
            "experience_level": "beginner",
            "age": 35,
            "weight_kg": 80.0,
        },
        "goals_focus": {
            "primary_goal": "finish",
            "weekly_availability": 4,
            "longest_recent_distance_m": 10000,
        },
        "plan_config": {
            "total_weeks": 14,
        },
    }


@pytest.fixture()
def guarded_client():
    """Client with isSwimmingEnabled disabled."""
    engine = _make_engine()
    _seed_flag(engine, "isSwimmingEnabled", [])
    app.dependency_overrides[get_session] = _session_override(engine)
    app.dependency_overrides[get_current_user] = _user_override(engine)
    app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def swimming_enabled_client():
    """Client with isSwimmingEnabled on for all."""
    engine = _make_engine()
    _seed_flag(engine, "isSwimmingEnabled", ["*"])
    app.dependency_overrides[get_session] = _session_override(engine)
    app.dependency_overrides[get_current_user] = _user_override(engine)
    app.dependency_overrides[verify_jwt_middleware] = _make_jwt_override()

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


class TestSwimmingGuard:
    def test_generate_preview_blocked_when_swimming_disabled(self, guarded_client):
        response = guarded_client.post(
            "/api/plans/generate-preview", json=_swimming_wizard_payload()
        )
        assert response.status_code == 403
        assert "not enabled" in response.json()["detail"].lower()

    def test_from_wizard_blocked_when_swimming_disabled(self, guarded_client):
        response = guarded_client.post(
            "/api/plans/from-wizard", json=_swimming_wizard_payload()
        )
        assert response.status_code == 403

    def test_update_from_wizard_blocked_when_swimming_disabled(self, guarded_client):
        response = guarded_client.put(
            "/api/plans/999/from-wizard", json=_swimming_wizard_payload()
        )
        assert response.status_code == 403

    def test_generate_preview_allowed_when_swimming_enabled(
        self, swimming_enabled_client
    ):
        """With the flag on, the guard passes (endpoint may still fail for other reasons
        — 400/500 is fine, but not 403)."""
        response = swimming_enabled_client.post(
            "/api/plans/generate-preview", json=_swimming_wizard_payload()
        )
        assert response.status_code != 403

    def test_running_plan_never_blocked_by_swimming_guard(self, guarded_client):
        """Running wizard payloads must not be blocked regardless of swimming flag state."""
        response = guarded_client.post(
            "/api/plans/generate-preview", json=_running_wizard_payload()
        )
        assert response.status_code != 403

    def test_all_three_endpoints_blocked_consistently(self, guarded_client):
        """All three wizard mutation endpoints enforce the guard."""
        payload = _swimming_wizard_payload()
        assert (
            guarded_client.post("/api/plans/generate-preview", json=payload).status_code
            == 403
        )
        assert (
            guarded_client.post("/api/plans/from-wizard", json=payload).status_code
            == 403
        )
        assert (
            guarded_client.put("/api/plans/999/from-wizard", json=payload).status_code
            == 403
        )
