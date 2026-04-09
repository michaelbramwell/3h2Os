from sqlmodel import Session, select
from typing import List
import json
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
        Saves a list of activities. Updates if activity already exists, else inserts.

        Precedence rules:
        - When saving a Strava activity, if a Garmin record exists for the same date
          and distance (within 1% tolerance), the Garmin record is upgraded to Strava
          data (preserving training_load, aerobic_te, anaerobic_te from Garmin).
        - When saving a Garmin activity, if a Strava record already exists for the same
          date and distance, the Garmin record is silently skipped.

        Returns count of saved activities.
        """
        if not user:
            raise ValueError(
                "save_activities requires a User — caller must resolve the user first"
            )

        count = 0

        def dump_zones(zones):
            if not zones:
                return None
            try:
                return json.dumps(
                    [z.model_dump() if hasattr(z, "model_dump") else z for z in zones]
                )
            except Exception:
                return None

        for act in activities:
            act_date = date.fromisoformat(act.date)
            source = act.source if act.source else "garmin"

            if source == "strava":
                self._save_strava_activity(act, act_date, user, dump_zones)
            else:
                saved = self._save_garmin_activity(act, act_date, user, dump_zones)
                if not saved:
                    continue
            count += 1

        self.session.commit()
        return count

    def _save_strava_activity(self, act, act_date, user, dump_zones):
        """
        Upsert a Strava activity. If a matching Garmin record exists, upgrade it.
        Preserve training_load, aerobic_te, anaerobic_te from the Garmin row.
        """
        # First check for exact Strava ID match (already imported)
        if act.stravaActivityId:
            existing = self.session.exec(
                select(ActualActivity).where(
                    ActualActivity.strava_activity_id == act.stravaActivityId,
                    ActualActivity.user_id == user.id,
                )
            ).first()
            if existing:
                self._apply_strava_data(existing, act, act_date, user, dump_zones)
                self.session.add(existing)
                return

        # Check for a Garmin record on same date + distance within 1%
        garmin_match = self._find_matching_activity(
            user_id=user.id,
            act_date=act_date,
            distance_m=act.distance_m,
            exclude_source="strava",
        )
        if garmin_match:
            # Preserve Garmin-only fields before overwriting
            preserved_training_load = garmin_match.training_load
            preserved_aerobic_te = garmin_match.aerobic_te
            preserved_anaerobic_te = garmin_match.anaerobic_te
            self._apply_strava_data(garmin_match, act, act_date, user, dump_zones)
            # Restore Garmin-only fields (training_load wins from Garmin per spec)
            if preserved_training_load is not None:
                garmin_match.training_load = preserved_training_load
            if preserved_aerobic_te is not None:
                garmin_match.aerobic_te = preserved_aerobic_te
            if preserved_anaerobic_te is not None:
                garmin_match.anaerobic_te = preserved_anaerobic_te
            self.session.add(garmin_match)
            return

        # No existing record — insert new Strava row
        new_act = ActualActivity(
            user_id=user.id,
            activity_id=None,
            strava_activity_id=act.stravaActivityId,
            source="strava",
            date=act_date,
            name=act.name,
            type=act.type,
            distance_m=act.distance_m,
            duration_s=act.duration_s,
            average_pace_m_s=act.average_pace_m_s,
            average_hr=act.average_hr,
            max_hr=act.max_hr,
            average_power=act.average_power,
            aerobic_te=None,
            anaerobic_te=None,
            training_load=act.training_load,
            calories=act.calories,
            hr_zones_json=dump_zones(act.hr_zones),
            pace_zones_json=dump_zones(act.pace_zones),
            power_zones_json=dump_zones(act.power_zones),
            splits_json=dump_zones(act.splits),
        )
        self.session.add(new_act)

    def _save_garmin_activity(self, act, act_date, user, dump_zones) -> bool:
        """
        Upsert a Garmin activity. If a Strava record already covers this date +
        distance, patch Garmin-only fields (aerobic_te, anaerobic_te, training_load)
        onto it rather than skipping entirely.
        """
        # If Strava already has this activity, enrich it with Garmin-only metrics
        strava_match = self._find_matching_activity(
            user_id=user.id,
            act_date=act_date,
            distance_m=act.distance_m,
            require_source="strava",
        )
        if strava_match:
            updated = False
            if act.aerobic_te is not None and strava_match.aerobic_te is None:
                strava_match.aerobic_te = act.aerobic_te
                updated = True
            if act.anaerobic_te is not None and strava_match.anaerobic_te is None:
                strava_match.anaerobic_te = act.anaerobic_te
                updated = True
            if act.training_load is not None and strava_match.training_load is None:
                strava_match.training_load = act.training_load
                updated = True
            if updated:
                self.session.add(strava_match)
            return updated  # Return True if enrichment was applied

        # Check for existing Garmin record by activity_id
        existing = None
        if act.activityId:
            existing = self.session.exec(
                select(ActualActivity).where(
                    ActualActivity.activity_id == act.activityId,
                    ActualActivity.user_id == user.id,
                )
            ).first()

        data = {
            "user_id": user.id,
            "date": act_date,
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
            "source": "garmin",
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
            self.session.add(existing)
        else:
            new_act = ActualActivity(activity_id=act.activityId, **data)
            self.session.add(new_act)
        return True

    def _apply_strava_data(self, row: ActualActivity, act, act_date, user, dump_zones):
        """Apply Strava fields onto an existing DB row (upgrade from Garmin or update Strava)."""
        row.source = "strava"
        row.strava_activity_id = act.stravaActivityId
        row.activity_id = None  # Clear Garmin ID when upgrading to Strava
        row.date = act_date
        row.name = act.name
        row.type = act.type
        row.distance_m = act.distance_m
        row.duration_s = act.duration_s
        row.average_pace_m_s = act.average_pace_m_s
        row.average_hr = act.average_hr
        row.max_hr = act.max_hr
        row.average_power = act.average_power
        row.calories = act.calories
        row.hr_zones_json = dump_zones(act.hr_zones)
        row.pace_zones_json = dump_zones(act.pace_zones)
        row.power_zones_json = dump_zones(act.power_zones)
        row.splits_json = dump_zones(act.splits)
        row.training_load = act.training_load
        # aerobic_te / anaerobic_te intentionally not overwritten here;
        # callers preserve or overwrite as appropriate.

    def _find_matching_activity(
        self,
        user_id: int,
        act_date,
        distance_m: float,
        require_source: str = None,
        exclude_source: str = None,
    ):
        """
        Find an existing activity on the same date with distance within 1% tolerance.
        Optionally filter by required source or exclude a source.
        """
        query = select(ActualActivity).where(
            ActualActivity.user_id == user_id,
            ActualActivity.date == act_date,
        )
        if require_source:
            query = query.where(ActualActivity.source == require_source)
        if exclude_source:
            query = query.where(ActualActivity.source != exclude_source)

        candidates = self.session.exec(query).all()
        for row in candidates:
            if row.distance_m and distance_m and distance_m > 0:
                diff = abs(row.distance_m - distance_m) / distance_m
                if diff < 0.01:
                    return row
        return None

    def get_activities(
        self, user: User, filter_types: List[str] = None
    ) -> List[ActivitySchema]:
        if not user:
            raise ValueError(
                "get_activities requires a User — caller must resolve the user first"
            )

        if not user:
            return []

        query = select(ActualActivity).where(ActualActivity.user_id == user.id)

        if filter_types:
            query = query.where(ActualActivity.type.in_(filter_types))

        activities = self.session.exec(query.order_by(ActualActivity.date)).all()

        result = []
        for a in activities:
            hr_zones = []
            if a.hr_zones_json:
                try:
                    raw_zones = json.loads(a.hr_zones_json)
                    hr_zones = [HrZone(**z) for z in raw_zones]
                except Exception:
                    pass

            pace_zones = []
            if a.pace_zones_json:
                try:
                    raw_zones = json.loads(a.pace_zones_json)
                    pace_zones = [HrZone(**z) for z in raw_zones]
                except Exception:
                    pass

            power_zones = []
            if a.power_zones_json:
                try:
                    raw_zones = json.loads(a.power_zones_json)
                    power_zones = [HrZone(**z) for z in raw_zones]
                except Exception:
                    pass

            splits = []
            if a.splits_json:
                try:
                    splits = json.loads(a.splits_json)
                except Exception:
                    pass

            result.append(
                ActivitySchema(
                    id=a.id,
                    date=a.date.isoformat(),
                    name=a.name,
                    custom_name=a.custom_name,
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
                    hr_zones=hr_zones,
                    pace_zones=pace_zones,
                    power_zones=power_zones,
                    splits=splits,
                )
            )
        return result
