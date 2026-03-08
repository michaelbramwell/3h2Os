import logging
from typing import List, Dict, Any
from sqlmodel import Session
from datetime import datetime, timedelta
from dataclasses import asdict

from app.core.database import User
from app.services.garmin import GarminService
from app.services.strava import StravaService
from app.services.activities import ActivityService
from app.services.plans import PlanService
from app.services.context import ContextService
from app.schemas import ActivitySchema

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, session: Session):
        self.session = session
        self.activity_service = ActivityService(session)
        self.plan_service = PlanService(session)
        self.context_service = ContextService(session)

    def sync_garmin(self, user: User, token: str, days: int = 7) -> int:
        """
        Sync Garmin activities for the last N days.
        Returns the number of activities saved.
        """
        with GarminService(self.session, token_b64=token) as garmin_service:
            if not garmin_service.client:
                raise ValueError("Garmin token invalid or expired")

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            activities = garmin_service.fetch_activities(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                user=user,
            )

            try:
                garmin_service.fetch_user_profile(user.id)
            except Exception as gpe:
                logger.warning(f"Garmin profile import failed (non-fatal): {gpe}")

            schema_activities = [ActivitySchema(**asdict(a)) for a in activities]

            count = self.activity_service.save_activities(schema_activities, user=user)

            try:
                self.plan_service.recalculate_plan_progression(user)
                logger.info(f"Triggered plan recalculation for user {user.username}")
            except Exception as pe:
                logger.error(f"Plan recalculation failed after sync: {pe}")

            return count

    def sync_strava(self, user: User, days: int = 7) -> int:
        """
        Sync Strava activities for the last N days.
        Returns the number of activities saved.
        """
        strava = StravaService(self.session)

        hr_thresholds = []
        pace_thresholds = []
        power_thresholds = []

        try:
            ctx = self.context_service.get_context(user=user)
            if ctx.runner and ctx.runner.trainingZones:
                if ctx.runner.trainingZones.heartRate:
                    hr_thresholds = [
                        z.model_dump() for z in ctx.runner.trainingZones.heartRate
                    ]
                if ctx.runner.trainingZones.pace:
                    pace_thresholds = [
                        z.model_dump() for z in ctx.runner.trainingZones.pace
                    ]
        except Exception as e:
            logger.warning(f"Could not load zone thresholds for Strava sync: {e}")

        activities = strava.sync_activities(
            user=user,
            days=days,
            hr_thresholds=hr_thresholds,
            pace_thresholds=pace_thresholds,
            power_thresholds=power_thresholds,
        )

        saved_count = self.activity_service.save_activities(activities, user=user)

        try:
            self.plan_service.recalculate_plan_progression(user)
        except Exception as e:
            logger.warning(
                f"Could not recalculate plan progression after Strava sync: {e}"
            )

        return saved_count
