"""
Tests for:
  - profile_sync.py: load_prefs, dump_prefs, can_write, apply_toggle
  - routers/profile.py: GET /profile, PATCH /profile, PATCH /profile/sync-prefs,
                        POST /profile/sync-now
"""

import json
import pytest

from fastapi import Request
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.database import RunnerProfile, StravaToken, User
from app.core.profile_sync import (
    DEFAULTS,
    SHARED_FIELDS,
    apply_toggle,
    can_write,
    dump_prefs,
    load_prefs,
)


# ---------------------------------------------------------------------------
# profile_sync.py unit tests
# ---------------------------------------------------------------------------


class TestLoadPrefs:
    def test_returns_defaults_when_none(self):
        prefs = load_prefs(None)
        assert prefs["strava"]["weight"] is True
        assert prefs["garmin"]["weight"] is False  # Strava wins by default
        assert prefs["strava"]["ftp"] is True
        assert prefs["garmin"]["resting_hr"] is True

    def test_merges_stored_values(self):
        stored = {"strava": {"weight": False}, "garmin": {"resting_hr": False}}
        prefs = load_prefs(json.dumps(stored))
        assert prefs["strava"]["weight"] is False  # overridden
        assert prefs["strava"]["ftp"] is True  # default still present
        assert prefs["garmin"]["resting_hr"] is False  # overridden
        assert prefs["garmin"]["height"] is True  # default still present

    def test_handles_corrupt_json(self):
        prefs = load_prefs("{invalid json")
        # Should fall back to defaults without raising
        assert prefs["strava"]["weight"] is True

    def test_fully_populated(self):
        prefs = load_prefs(None)
        for source, fields in DEFAULTS.items():
            for field in fields:
                assert field in prefs[source]


class TestDumpPrefs:
    def test_roundtrip(self):
        prefs = load_prefs(None)
        serialised = dump_prefs(prefs)
        restored = load_prefs(serialised)
        assert restored == prefs

    def test_compact_json(self):
        prefs = load_prefs(None)
        s = dump_prefs(prefs)
        # No extra whitespace
        assert " " not in s


class TestCanWrite:
    def test_garmin_can_write_owned_fields(self):
        prefs = load_prefs(None)
        # garmin owns height/resting_hr/vo2max/lactate_threshold by default
        assert (
            can_write(prefs, "garmin", "weight") is False
        )  # strava owns weight by default
        assert can_write(prefs, "garmin", "height") is True
        assert can_write(prefs, "garmin", "resting_hr") is True
        assert can_write(prefs, "garmin", "vo2max") is True
        assert can_write(prefs, "garmin", "lactate_threshold") is True

    def test_strava_can_write_weight_by_default(self):
        prefs = load_prefs(None)
        # Strava weight default is True
        assert can_write(prefs, "strava", "weight") is True

    def test_strava_can_write_ftp_and_hr_zones(self):
        prefs = load_prefs(None)
        assert can_write(prefs, "strava", "ftp") is True
        assert can_write(prefs, "strava", "hr_zones") is True

    def test_disabled_field_returns_false(self):
        prefs = load_prefs(None)
        prefs["garmin"]["resting_hr"] = False
        assert can_write(prefs, "garmin", "resting_hr") is False

    def test_mutual_exclusion_strava_wins_when_both_true(self):
        """If both garmin and strava weight are True (corrupted state), strava wins."""
        prefs = load_prefs(None)
        prefs["garmin"]["weight"] = True
        prefs["strava"]["weight"] = True
        winning_source = SHARED_FIELDS["weight"][0]  # "strava"
        assert can_write(prefs, winning_source, "weight") is True
        assert can_write(prefs, "garmin", "weight") is False


class TestApplyToggle:
    def test_enable_field(self):
        prefs = load_prefs(None)
        prefs["garmin"]["resting_hr"] = False
        result = apply_toggle(prefs, "garmin", "resting_hr", True)
        assert result["garmin"]["resting_hr"] is True

    def test_disable_field(self):
        prefs = load_prefs(None)
        result = apply_toggle(prefs, "strava", "weight", False)
        assert result["strava"]["weight"] is False

    def test_enabling_garmin_weight_disables_strava_weight(self):
        prefs = load_prefs(None)
        assert prefs["strava"]["weight"] is True  # strava owns weight by default
        result = apply_toggle(prefs, "garmin", "weight", True)
        assert result["garmin"]["weight"] is True
        assert result["strava"]["weight"] is False

    def test_enabling_strava_weight_disables_garmin_weight(self):
        # Start with garmin weight enabled, strava disabled
        prefs = load_prefs(None)
        prefs["garmin"]["weight"] = True
        prefs["strava"]["weight"] = False
        result = apply_toggle(prefs, "strava", "weight", True)
        assert result["strava"]["weight"] is True
        assert result["garmin"]["weight"] is False

    def test_disabling_shared_field_does_not_affect_other_source(self):
        prefs = load_prefs(None)
        # Disable strava weight — garmin weight stays False (its own default)
        result = apply_toggle(prefs, "strava", "weight", False)
        assert result["strava"]["weight"] is False
        assert result["garmin"]["weight"] is False  # unchanged

    def test_does_not_mutate_input(self):
        prefs = load_prefs(None)
        original_val = prefs["strava"]["weight"]
        apply_toggle(prefs, "strava", "weight", not original_val)
        assert prefs["strava"]["weight"] == original_val  # original untouched


# ---------------------------------------------------------------------------
# Router tests (HTTP layer)
# ---------------------------------------------------------------------------


def _make_app_overrides(session: Session, user: User):
    """Return (override_session, override_user, override_jwt) callables."""
    from app.core.database import get_session
    from app.core.auth import verify_jwt_middleware
    from app.routers.deps import get_current_user

    def override_session():
        yield session

    async def override_user():
        return user

    async def override_jwt(request: Request):
        pass  # bypass JWT check

    return {
        get_session: override_session,
        get_current_user: override_user,
        verify_jwt_middleware: override_jwt,
    }


@pytest.fixture
def app_client(session: Session):
    """
    TestClient with the real FastAPI app but using in-memory SQLite.
    Overrides the DB session and authentication dependencies.
    """
    from app.main import app

    # Create a test user + profile
    user = User(username="testprofile", email="testprofile@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    profile = RunnerProfile(
        user_id=user.id,
        age=35,
        gender="male",
        height_cm=180,
        weight_kg=75.0,
    )
    session.add(profile)
    session.commit()

    overrides = _make_app_overrides(session, user)
    app.dependency_overrides.update(overrides)

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    app.dependency_overrides.clear()


class TestGetProfile:
    def test_returns_profile(self, app_client):
        resp = app_client.get("/api/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["age"] == 35
        assert data["gender"] == "male"
        assert data["height_cm"] == 180
        assert data["weight_kg"] == 75.0

    def test_includes_sync_prefs(self, app_client):
        resp = app_client.get("/api/profile")
        data = resp.json()
        assert "sync_prefs" in data
        assert data["sync_prefs"]["strava"]["weight"] is True  # Strava wins by default
        assert data["sync_prefs"]["garmin"]["weight"] is False

    def test_404_when_no_profile(self, session: Session):
        """A user with no RunnerProfile row gets a 404."""
        from app.main import app

        user = User(username="noprofile", email="noprofile@example.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        overrides = _make_app_overrides(session, user)
        app.dependency_overrides.update(overrides)

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/profile")
        assert resp.status_code == 404

        app.dependency_overrides.clear()


class TestPatchProfile:
    def test_updates_manual_field(self, app_client):
        resp = app_client.patch("/api/profile", json={"age": 40})
        assert resp.status_code == 200
        assert resp.json()["age"] == 40

    def test_skips_source_owned_field(self, app_client):
        """weight_kg is owned by strava by default — manual edit is silently ignored."""
        resp = app_client.patch("/api/profile", json={"weight_kg": 999.0})
        assert resp.status_code == 200
        # weight should be unchanged (still 75.0 from fixture)
        assert resp.json()["weight_kg"] == 75.0

    def test_invalid_age_rejected(self, app_client):
        resp = app_client.patch("/api/profile", json={"age": 5})
        assert resp.status_code == 422

    def test_invalid_gender_rejected(self, app_client):
        resp = app_client.patch("/api/profile", json={"gender": "alien"})
        assert resp.status_code == 422

    def test_updates_experience_level(self, app_client):
        resp = app_client.patch(
            "/api/profile", json={"experience_level": "intermediate"}
        )
        assert resp.status_code == 200
        assert resp.json()["experience_level"] == "intermediate"


class TestPatchSyncPrefs:
    def test_disable_garmin_weight(self, app_client):
        resp = app_client.patch(
            "/api/profile/sync-prefs",
            json={"source": "garmin", "field": "weight", "enabled": False},
        )
        assert resp.status_code == 200
        assert resp.json()["garmin"]["weight"] is False

    def test_enable_strava_weight_disables_garmin_weight(self, app_client):
        resp = app_client.patch(
            "/api/profile/sync-prefs",
            json={"source": "strava", "field": "weight", "enabled": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["strava"]["weight"] is True
        assert data["garmin"]["weight"] is False

    def test_invalid_source_rejected(self, app_client):
        resp = app_client.patch(
            "/api/profile/sync-prefs",
            json={"source": "fitbit", "field": "weight", "enabled": True},
        )
        assert resp.status_code == 422

    def test_invalid_field_for_source_rejected(self, app_client):
        resp = app_client.patch(
            "/api/profile/sync-prefs",
            json={"source": "garmin", "field": "ftp", "enabled": True},
        )
        # ftp is a strava field, not garmin
        assert resp.status_code == 422


class TestSyncNow:
    def test_returns_ok_no_strava(self, app_client):
        """sync-now with no Strava token connected returns ok with empty synced_sources."""
        resp = app_client.post("/api/profile/sync-now")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "strava" not in data["synced_sources"]
