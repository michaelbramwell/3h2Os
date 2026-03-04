"""
Unit tests for FeatureFlagService.
"""

import json
import pytest
from sqlmodel import Session

from app.core.database import FeatureFlag, User
from app.services.feature_flags import FeatureFlagService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user(
    session: Session, username: str = "runner", types: list[str] = None
) -> User:
    types = types if types is not None else ["standard"]
    user = User(
        username=username,
        email=f"{username}@example.com",
        user_types_json=json.dumps(types),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def make_flag(
    session: Session, name: str, enabled_for: list[str], description: str = None
) -> FeatureFlag:
    flag = FeatureFlag(
        name=name,
        enabled_for_json=json.dumps(enabled_for),
        description=description,
    )
    session.add(flag)
    session.commit()
    session.refresh(flag)
    return flag


# ---------------------------------------------------------------------------
# _user_types
# ---------------------------------------------------------------------------


class TestUserTypes:
    def test_standard_user(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["standard"])
        assert svc._user_types(user) == {"standard"}

    def test_multiple_types(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["alpha", "beta"])
        assert svc._user_types(user) == {"alpha", "beta"}

    def test_null_user_types_defaults_to_standard(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session)
        user.user_types_json = None
        assert svc._user_types(user) == {"standard"}

    def test_malformed_json_defaults_to_standard(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session)
        user.user_types_json = "not-valid-json"
        assert svc._user_types(user) == {"standard"}


# ---------------------------------------------------------------------------
# _flag_enabled_for
# ---------------------------------------------------------------------------


class TestFlagEnabledFor:
    def test_empty_list_is_disabled_for_everyone(self, session: Session):
        svc = FeatureFlagService(session)
        flag = make_flag(session, "f", [])
        assert svc._flag_enabled_for(flag, {"standard"}) is False
        assert svc._flag_enabled_for(flag, {"alpha"}) is False

    def test_wildcard_enables_for_everyone(self, session: Session):
        svc = FeatureFlagService(session)
        flag = make_flag(session, "f", ["*"])
        assert svc._flag_enabled_for(flag, {"standard"}) is True
        assert svc._flag_enabled_for(flag, {"alpha", "beta"}) is True
        assert svc._flag_enabled_for(flag, set()) is True

    def test_specific_type_match(self, session: Session):
        svc = FeatureFlagService(session)
        flag = make_flag(session, "f", ["alpha"])
        assert svc._flag_enabled_for(flag, {"alpha"}) is True
        assert svc._flag_enabled_for(flag, {"standard"}) is False

    def test_any_matching_type_enables(self, session: Session):
        svc = FeatureFlagService(session)
        flag = make_flag(session, "f", ["alpha", "beta"])
        assert svc._flag_enabled_for(flag, {"beta"}) is True
        assert svc._flag_enabled_for(flag, {"standard"}) is False
        assert svc._flag_enabled_for(flag, {"standard", "alpha"}) is True

    def test_malformed_enabled_for_json_is_disabled(self, session: Session):
        svc = FeatureFlagService(session)
        flag = make_flag(session, "f", [])
        flag.enabled_for_json = "not-json"
        assert svc._flag_enabled_for(flag, {"standard"}) is False


# ---------------------------------------------------------------------------
# is_enabled
# ---------------------------------------------------------------------------


class TestIsEnabled:
    def test_flag_not_found_returns_false(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session)
        assert svc.is_enabled("nonexistent", user) is False

    def test_flag_off_returns_false(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["standard"])
        make_flag(session, "isSwimmingEnabled", [])
        assert svc.is_enabled("isSwimmingEnabled", user) is False

    def test_flag_on_for_matching_user(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["alpha"])
        make_flag(session, "isSwimmingEnabled", ["alpha"])
        assert svc.is_enabled("isSwimmingEnabled", user) is True

    def test_flag_on_for_all_users(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["standard"])
        make_flag(session, "isSwimmingEnabled", ["*"])
        assert svc.is_enabled("isSwimmingEnabled", user) is True

    def test_flag_off_for_non_matching_user(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["standard"])
        make_flag(session, "isSwimmingEnabled", ["alpha"])
        assert svc.is_enabled("isSwimmingEnabled", user) is False


# ---------------------------------------------------------------------------
# get_flags_for_user
# ---------------------------------------------------------------------------


class TestGetFlagsForUser:
    def test_empty_db_returns_empty_dict(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session)
        assert svc.get_flags_for_user(user) == {}

    def test_returns_all_flags_resolved(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["alpha"])
        make_flag(session, "isSwimmingEnabled", ["alpha"])
        make_flag(session, "someBetaFeature", ["beta"])
        make_flag(session, "globalFlag", ["*"])

        result = svc.get_flags_for_user(user)
        assert result == {
            "isSwimmingEnabled": True,
            "someBetaFeature": False,
            "globalFlag": True,
        }

    def test_standard_user_sees_only_global_flags(self, session: Session):
        svc = FeatureFlagService(session)
        user = make_user(session, types=["standard"])
        make_flag(session, "alphaOnly", ["alpha"])
        make_flag(session, "forAll", ["*"])

        result = svc.get_flags_for_user(user)
        assert result["alphaOnly"] is False
        assert result["forAll"] is True


# ---------------------------------------------------------------------------
# set_flag (create + update)
# ---------------------------------------------------------------------------


class TestSetFlag:
    def test_creates_new_flag(self, session: Session):
        svc = FeatureFlagService(session)
        flag = svc.set_flag("newFlag", ["alpha"], description="test desc")
        assert flag.name == "newFlag"
        assert json.loads(flag.enabled_for_json) == ["alpha"]
        assert flag.description == "test desc"

    def test_updates_existing_flag(self, session: Session):
        svc = FeatureFlagService(session)
        make_flag(session, "myFlag", [])
        updated = svc.set_flag("myFlag", ["*"])
        assert json.loads(updated.enabled_for_json) == ["*"]

    def test_description_not_overwritten_when_none(self, session: Session):
        svc = FeatureFlagService(session)
        make_flag(session, "myFlag", [], description="original")
        updated = svc.set_flag("myFlag", ["beta"], description=None)
        assert updated.description == "original"

    def test_description_updated_when_provided(self, session: Session):
        svc = FeatureFlagService(session)
        make_flag(session, "myFlag", [], description="old")
        updated = svc.set_flag("myFlag", ["beta"], description="new")
        assert updated.description == "new"


# ---------------------------------------------------------------------------
# list_flags
# ---------------------------------------------------------------------------


class TestListFlags:
    def test_empty_db(self, session: Session):
        svc = FeatureFlagService(session)
        assert svc.list_flags() == []

    def test_returns_all_flags(self, session: Session):
        svc = FeatureFlagService(session)
        make_flag(session, "flag1", [])
        make_flag(session, "flag2", ["*"])
        flags = svc.list_flags()
        names = {f.name for f in flags}
        assert names == {"flag1", "flag2"}
