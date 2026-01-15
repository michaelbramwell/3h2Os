from sqlmodel import Session, select
import json
import os

from app.core.database import User
from app.schemas import ContextSchema, ProjectContext, RunnerContext, WeightContext, WeightRecord

class ContextService:
    def __init__(self, session: Session):
        self.session = session

    def get_context(self, username: str = "mike") -> ContextSchema:
        """
        Retrieves the Context (Project + Runner Profile).
        """
        # Try DB
        user = self.session.exec(select(User).where(User.username == username)).first()
        if user and user.project and user.profile:
            return self._map_to_schema(user)

        # Fallback File
        if os.path.exists("data/context.json"):
            with open("data/context.json", "r") as f:
                return ContextSchema.model_validate(json.load(f))
        
        # Empty
        return self._empty_context()

    def _map_to_schema(self, user: User) -> ContextSchema:
        project_ctx = ProjectContext.model_validate(user.project)

        weights = [
            WeightRecord(date=str(w.date_recorded), weight=w.weight_kg) 
            for w in sorted(user.profile.weight_history, key=lambda x: x.date_recorded)
        ]
        
        weight_ctx = WeightContext(
            current=user.profile.current_weight,
            target=user.profile.target_weight,
            history=weights
        )

        runner_ctx = RunnerContext(
            age=user.profile.age,
            gender=user.profile.gender,
            height_cm=user.profile.height_cm,
            weight_kg=weight_ctx
        )
        return ContextSchema(project=project_ctx, runner=runner_ctx)

    def _empty_context(self) -> ContextSchema:
        return ContextSchema(
            project=ProjectContext(name="", goal="", event="", eventDate=""),
            runner=RunnerContext(age=0, gender="", height_cm=0, weight_kg=WeightContext(current=0, target=0))
        )
