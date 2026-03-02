"""
Feature flag service.

Flags are stored in the FeatureFlag table.  Each flag has an `enabled_for_json`
field that is a JSON array of user-type strings:
  - '[]'          → disabled for everyone
  - '["*"]'       → enabled for everyone
  - '["alpha","beta"]' → enabled only for users that have at least one matching type

A user's types are stored in User.user_types_json as a JSON array.
"""

import json
from sqlmodel import Session, select

from app.core.database import FeatureFlag, User


class FeatureFlagService:
    def __init__(self, session: Session):
        self.session = session

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _user_types(self, user: User) -> set[str]:
        """Return the set of type strings for a user."""
        try:
            types = json.loads(user.user_types_json or '["standard"]')
            return set(types)
        except (json.JSONDecodeError, TypeError):
            return {"standard"}

    def _flag_enabled_for(self, flag: FeatureFlag, user_types: set[str]) -> bool:
        """Return True if the flag is enabled for the given set of user types."""
        try:
            enabled_for = json.loads(flag.enabled_for_json or "[]")
        except (json.JSONDecodeError, TypeError):
            return False

        if not enabled_for:
            return False
        if "*" in enabled_for:
            return True
        # User passes if they have ANY matching type
        return bool(user_types & set(enabled_for))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_flags_for_user(self, user: User) -> dict[str, bool]:
        """
        Return a dict of {flag_name: bool} for the given user,
        covering all flags currently in the database.
        """
        flags = self.session.exec(select(FeatureFlag)).all()
        user_types = self._user_types(user)
        return {flag.name: self._flag_enabled_for(flag, user_types) for flag in flags}

    def is_enabled(self, flag_name: str, user: User) -> bool:
        """Return True if the named flag is enabled for the given user."""
        flag = self.session.exec(
            select(FeatureFlag).where(FeatureFlag.name == flag_name)
        ).first()
        if flag is None:
            return False
        return self._flag_enabled_for(flag, self._user_types(user))

    def set_flag(
        self, flag_name: str, enabled_for: list[str], description: str | None = None
    ) -> FeatureFlag:
        """
        Create or update a feature flag.
        `enabled_for` is a list of user type strings (or ["*"] for everyone, [] to disable).
        """
        flag = self.session.exec(
            select(FeatureFlag).where(FeatureFlag.name == flag_name)
        ).first()

        if flag is None:
            flag = FeatureFlag(name=flag_name)
            self.session.add(flag)

        flag.enabled_for_json = json.dumps(enabled_for)
        if description is not None:
            flag.description = description

        self.session.commit()
        self.session.refresh(flag)
        return flag

    def list_flags(self) -> list[FeatureFlag]:
        """Return all flags (admin use)."""
        return list(self.session.exec(select(FeatureFlag)).all())
