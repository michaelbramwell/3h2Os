from sqlmodel import Session, select
import json
import os

import logging

from app.core.database import User
from app.schemas import (
    ContextSchema,
    ProjectContext,
    RunnerContext,
    TrainingZones,
)
from datetime import date

logger = logging.getLogger(__name__)


class ContextService:
    def __init__(self, session: Session):
        self.session = session

    def get_context(self, user: User = None) -> ContextSchema:
        """
        Retrieves the Context (Project + Runner Profile).
        """
        if not user:
            username = os.environ.get("DEFAULT_USERNAME", "runner")
            # Try DB
            user = self.session.exec(
                select(User).where(User.username == username)
            ).first()

        if user and user.project and user.profile:
            return self._map_to_schema(user)

        # Empty
        return self._empty_context()

    def _map_to_schema(self, user: User) -> ContextSchema:
        project_ctx = ProjectContext.model_validate(user.project)

        # Parse JSON fields
        fueling = None
        if user.profile.fueling_json:
            try:
                fueling = json.loads(user.profile.fueling_json)
            except json.JSONDecodeError:
                # If fueling JSON is invalid, leave `fueling` as None and continue.
                pass

        zones = None
        if user.profile.training_zones_json:
            try:
                # Load JSON to dict
                zones_dict = json.loads(user.profile.training_zones_json)

                # Merge swim zones if available
                if user.profile.swim_zones_json:
                    try:
                        swim_zones_list = json.loads(user.profile.swim_zones_json)
                        if isinstance(swim_zones_list, list):
                            zones_dict["swimPace"] = swim_zones_list
                    except Exception as e:
                        logger.error(
                            f"Error parsing swim zones (type={type(e).__name__}) "
                            f"for swim_zones_json={user.profile.swim_zones_json!r}: {e}"
                        )

                # Ensure it's valid schema
                zones = TrainingZones.model_validate(zones_dict)
            except Exception as e:
                logger.error(f"Error parsing zones: {e}")

        runner_ctx = RunnerContext(
            age=user.profile.age,
            gender=user.profile.gender,
            height_cm=user.profile.height_cm,
            fueling=fueling,
            trainingZones=zones,
        )
        return ContextSchema(project=project_ctx, runner=runner_ctx)

    def _empty_context(self) -> ContextSchema:
        return ContextSchema(
            project=ProjectContext(name="", goal="", event="", eventDate=""),
            runner=RunnerContext(
                age=0,
                gender="",
                height_cm=0,
            ),
        )
