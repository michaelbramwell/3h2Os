from sqlmodel import Session, select
from typing import List
import json
import os
from datetime import date

from app.core.database import ActualActivity, User
from app.schemas import ActivitySchema, HrZone


class ActivityService:
    def __init__(self, session: Session):
        self.session = session

    def save_activities(
        self, activities: List[ActivitySchema], user: User = None
    ) -> int:
        """
        Saves a list of activities. Updates if activityId exists, else inserts.
        Returns count of saved activities.
        """
        if not user:
            username = os.environ.get("DEFAULT_USERNAME", "runner")
            user = self.session.exec(
                select(User).where(User.username == username)
            ).first()
            if not user:
                raise ValueError("User not found")

        count = 0
        for act in activities:
            # Check if exists
            existing = self.session.exec(
                select(ActualActivity).where(
                    ActualActivity.activity_id == act.activityId
                )
            ).first()

            # Helper to dump zones
            def dump_zones(zones):
                if not zones:
                    return None
                # Check if it's already a list of dicts or list of objects
                try:
                    return json.dumps(
                        [
                            z.model_dump() if hasattr(z, "model_dump") else z
                            for z in zones
                        ]
                    )
                except:
                    return None

            data = {
                "user_id": user.id,
                "date": date.fromisoformat(act.date),  # Expecting YYYY-MM-DD
                "name": act.name,
                "type": act.type,
                "distance_m": act.distance_m,
                "duration_s": act.duration_s,
                "average_pace_m_s": act.average_pace_m_s,
                "average_hr": act.average_hr,
                "max_hr": act.max_hr,
                "average_power": act.average_power,
                "aerobic_te": act.aerobic_te,
                "anaerobic_te": act.anaerobic_te,
                "training_load": act.training_load,
                "calories": act.calories,
                "hr_zones_json": dump_zones(act.hr_zones),
                "pace_zones_json": dump_zones(act.pace_zones),
                "power_zones_json": dump_zones(act.power_zones),
                "splits_json": dump_zones(act.splits),
            }

            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                self.session.add(existing)
            else:
                new_act = ActualActivity(activity_id=act.activityId, **data)
                self.session.add(new_act)
            count += 1

        self.session.commit()
        return count

    def get_activities(self, user: User = None) -> List[ActivitySchema]:
        if not user:
            username = os.environ.get("DEFAULT_USERNAME", "runner")
            user = self.session.exec(
                select(User).where(User.username == username)
            ).first()

        if not user:
            return []

        activities = self.session.exec(
            select(ActualActivity)
            .where(ActualActivity.user_id == user.id)
            .order_by(ActualActivity.date)
        ).all()

        result = []
        for a in activities:
            # Map back to Schema
            hr_zones = []
            if a.hr_zones_json:
                try:
                    raw_zones = json.loads(a.hr_zones_json)
                    hr_zones = [HrZone(**z) for z in raw_zones]
                except:
                    pass

            pace_zones = []
            if a.pace_zones_json:
                try:
                    raw_zones = json.loads(a.pace_zones_json)
                    pace_zones = [HrZone(**z) for z in raw_zones]
                except:
                    pass

            power_zones = []
            if a.power_zones_json:
                try:
                    raw_zones = json.loads(a.power_zones_json)
                    power_zones = [HrZone(**z) for z in raw_zones]
                except:
                    pass

            splits = []
            if a.splits_json:
                try:
                    splits = json.loads(a.splits_json)
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass

            result.append(
                ActivitySchema(
                    date=a.date.isoformat(),
                    name=a.name,
                    type=a.type,
                    distance_m=a.distance_m,
                    duration_s=a.duration_s,
                    activityId=a.activity_id,
                    average_pace_m_s=a.average_pace_m_s,
                    average_hr=a.average_hr,
                    max_hr=a.max_hr,
                    average_power=a.average_power,
                    aerobic_te=a.aerobic_te,
                    anaerobic_te=a.anaerobic_te,
                    training_load=a.training_load,
                    calories=a.calories,
                    hr_zones=hr_zones,
                    pace_zones=pace_zones,
                    power_zones=power_zones,
                    splits=splits,
                )
            )
        return result
