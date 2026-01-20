from sqlmodel import Session, select
import json
import os

from app.core.database import User, WeightEntry
from app.schemas import ContextSchema, ProjectContext, RunnerContext, WeightContext, WeightRecord
from datetime import date

class ContextService:
    def __init__(self, session: Session):
        self.session = session

    def update_weight(self, weight: float, username: str = None):
        """
        Updates the current weight and adds a history entry.
        """
        username = username or os.environ.get("DEFAULT_USERNAME", "runner")
        user = self.session.exec(select(User).where(User.username == username)).first()
        if not user or not user.profile:
            # Create profile if missing? For now assume user exists from init
            raise ValueError(f"User {username} or profile not found")

        # Update Current
        user.profile.current_weight = weight
        self.session.add(user.profile)
        
        # Add History
        today = date.today()
        # Check if entry exists for today
        existing = self.session.exec(
            select(WeightEntry)
            .where(WeightEntry.profile_id == user.profile.id)
            .where(WeightEntry.date_recorded == today)
        ).first()
        
        if existing:
            existing.weight_kg = weight
            self.session.add(existing)
        else:
            new_entry = WeightEntry(profile_id=user.profile.id, date_recorded=today, weight_kg=weight)
            self.session.add(new_entry)
            
        self.session.commit()
        return user.profile.current_weight

    def get_context(self, username: str = None) -> ContextSchema:
        """
        Retrieves the Context (Project + Runner Profile).
        """
        username = username or os.environ.get("DEFAULT_USERNAME", "runner")
        # Try DB
        user = self.session.exec(select(User).where(User.username == username)).first()
        if user and user.project and user.profile:
            return self._map_to_schema(user)

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
