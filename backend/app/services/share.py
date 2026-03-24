import secrets
import json
from typing import Optional

from sqlmodel import Session, select

from app.core.database import ActualActivity, ActivityShare
from app.schemas import ActivitySchema, HrZone


class ShareService:
    def __init__(self, session: Session):
        self.session = session

    def create_share(self, activity_id: int, user_id: int) -> ActivityShare:
        """
        Return the share record for the given activity, creating one if it does not
        exist yet. Raises ValueError if the activity does not belong to user_id.
        """
        activity = self.session.get(ActualActivity, activity_id)
        if activity is None or activity.user_id != user_id:
            raise ValueError("Activity not found or does not belong to user")

        existing = self.session.exec(
            select(ActivityShare).where(ActivityShare.activity_id == activity_id)
        ).first()
        if existing:
            return existing

        share = ActivityShare(
            activity_id=activity_id,
            token=secrets.token_hex(32),
        )
        self.session.add(share)
        self.session.commit()
        self.session.refresh(share)
        return share

    def get_activity_by_token(self, token: str) -> Optional[ActivitySchema]:
        """
        Look up the share record by token, then return the associated activity as
        an ActivitySchema. Returns None if the token is not found.
        """
        share = self.session.exec(
            select(ActivityShare).where(ActivityShare.token == token)
        ).first()
        if share is None:
            return None

        activity = self.session.get(ActualActivity, share.activity_id)
        if activity is None:
            return None

        return self._to_schema(activity)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_schema(self, a: ActualActivity) -> ActivitySchema:
        def parse_zones(raw: Optional[str]) -> Optional[list]:
            if not raw:
                return None
            try:
                data = json.loads(raw)
                return [HrZone(**z) for z in data]
            except Exception:
                return None

        splits = []
        if a.splits_json:
            try:
                splits = json.loads(a.splits_json)
            except Exception:
                pass

        return ActivitySchema(
            id=a.id,
            date=a.date.isoformat(),
            name=a.name,
            type=a.type,
            distance_m=a.distance_m,
            duration_s=a.duration_s,
            activityId=a.activity_id,
            stravaActivityId=a.strava_activity_id,
            source=a.source,
            average_pace_m_s=a.average_pace_m_s,
            average_hr=a.average_hr,
            max_hr=a.max_hr,
            average_power=a.average_power,
            aerobic_te=a.aerobic_te,
            anaerobic_te=a.anaerobic_te,
            training_load=a.training_load,
            calories=a.calories,
            hr_zones=parse_zones(a.hr_zones_json),
            pace_zones=parse_zones(a.pace_zones_json),
            power_zones=parse_zones(a.power_zones_json),
            splits=splits,
        )
