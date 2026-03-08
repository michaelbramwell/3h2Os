import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

import httpx
from sqlmodel import Session, select

from app.core.database import StravaToken, RunnerProfile, User
from app.schemas import ActivitySchema

logger = logging.getLogger(__name__)

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"
STRAVA_AUTH_BASE = "https://www.strava.com/oauth/authorize"

# Seconds before expiry at which we proactively refresh the access token
_REFRESH_BUFFER_SECS = 300

# State token TTL — callback must arrive within this window
_STATE_TTL_SECS = 600  # 10 minutes

# Default env var names
_CLIENT_ID_ENV = "STRAVA_CLIENT_ID"
_CLIENT_SECRET_ENV = "STRAVA_CLIENT_SECRET"
_REDIRECT_URI_ENV = "STRAVA_REDIRECT_URI"
_STREAMS_MAX_AGE_ENV = "STRAVA_STREAMS_MAX_AGE_DAYS"
_DEFAULT_REDIRECT_URI = "http://localhost:5173/strava/callback"
_DEFAULT_STREAMS_MAX_AGE_DAYS = 90


def _state_secret() -> str:
    secret = os.environ.get("STRAVA_STATE_SECRET") or os.environ.get("SECRET_KEY", "")
    if not secret:
        raise RuntimeError("STRAVA_STATE_SECRET env var is not set")
    return secret


def generate_state_token(user_id: int) -> str:
    """
    Generate a short-lived HMAC-signed state token encoding the user ID and
    a timestamp. Format: {user_id}:{ts}:{hmac}
    """
    ts = int(time.time())
    payload = f"{user_id}:{ts}"
    sig = hmac.new(
        _state_secret().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}:{sig}"


def verify_state_token(state: str) -> int:
    """
    Verify a state token and return the user_id it encodes.
    Raises ValueError if invalid, tampered, or expired.
    """
    try:
        user_id_str, ts_str, sig = state.rsplit(":", 2)
    except ValueError:
        raise ValueError("Malformed state token")

    payload = f"{user_id_str}:{ts_str}"
    expected_sig = hmac.new(
        _state_secret().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        raise ValueError("Invalid state token signature")

    ts = int(ts_str)
    if int(time.time()) - ts > _STATE_TTL_SECS:
        raise ValueError("State token expired")

    return int(user_id_str)


# Strava sport_type -> our internal type normalisation
_SPORT_TYPE_MAP: Dict[str, str] = {
    "Run": "running",
    "TrailRun": "trail_running",
    "VirtualRun": "running",
    "Walk": "walking",
    "Hike": "hiking",
    "Ride": "cycling",
    "VirtualRide": "cycling",
    "MountainBikeRide": "cycling",
    "Swim": "swimming",
    "Workout": "workout",
    "WeightTraining": "strength_training",
    "Yoga": "yoga",
}


class StravaService:
    """
    Handles all Strava OAuth and activity data operations for a given session.

    Usage:
        service = StravaService(session)
        token = service.get_token(user_id)
        token = service.refresh_if_needed(token)
        activities = service.fetch_activities(token.access_token, start_date, end_date)
    """

    def __init__(self, session: Session):
        self.session = session
        self.client_id = os.environ.get(_CLIENT_ID_ENV, "")
        self.client_secret = os.environ.get(_CLIENT_SECRET_ENV, "")
        self.redirect_uri = os.environ.get(_REDIRECT_URI_ENV, _DEFAULT_REDIRECT_URI)
        self.streams_max_age_days = int(
            os.environ.get(_STREAMS_MAX_AGE_ENV, _DEFAULT_STREAMS_MAX_AGE_DAYS)
        )

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------

    def get_auth_url(self, user_id: int) -> str:
        """Build the Strava OAuth authorization URL with a signed state token."""
        scope = "activity:read_all,profile:read_all"
        state = generate_state_token(user_id)
        return (
            f"{STRAVA_AUTH_BASE}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&approval_prompt=auto"
            f"&scope={scope}"
            f"&state={state}"
        )

    def exchange_code(self, code: str) -> Dict[str, Any]:
        """
        Exchange an authorization code for tokens.
        Returns the raw Strava token response dict.
        """
        response = httpx.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        if not response.is_success:
            logger.error(
                f"Strava token exchange failed {response.status_code}: {response.text}"
            )
        response.raise_for_status()
        return response.json()

    def save_token(self, user_id: int, token_data: Dict[str, Any]) -> StravaToken:
        """
        Upsert a StravaToken row from the raw Strava token response dict.
        Handles both initial exchange and refresh responses.
        """
        athlete = token_data.get("athlete", {})
        athlete_id = athlete.get("id") if athlete else token_data.get("athlete_id")
        if athlete_id is None:
            raise ValueError("Token data missing athlete id")

        existing = self.session.exec(
            select(StravaToken).where(StravaToken.user_id == user_id)
        ).first()

        now = datetime.utcnow()

        if existing:
            existing.athlete_id = athlete_id
            existing.access_token = token_data["access_token"]
            existing.refresh_token = token_data["refresh_token"]
            existing.expires_at = token_data["expires_at"]
            existing.scope = token_data.get("scope", existing.scope)
            existing.updated_at = now
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        token = StravaToken(
            user_id=user_id,
            athlete_id=athlete_id,
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=token_data["expires_at"],
            scope=token_data.get("scope", "activity:read_all,profile:read_all"),
            created_at=now,
            updated_at=now,
        )
        self.session.add(token)
        self.session.commit()
        self.session.refresh(token)
        return token

    def get_token(self, user_id: int) -> Optional[StravaToken]:
        """Fetch the stored token for a user. Returns None if not connected."""
        return self.session.exec(
            select(StravaToken).where(StravaToken.user_id == user_id)
        ).first()

    def refresh_if_needed(self, token: StravaToken) -> StravaToken:
        """
        If the access token expires within _REFRESH_BUFFER_SECS, refresh it and
        persist the updated token. Returns the (possibly refreshed) token.
        """
        now = int(time.time())
        if token.expires_at - now > _REFRESH_BUFFER_SECS:
            return token

        logger.info(
            f"Refreshing Strava token for user_id={token.user_id} "
            f"(expires_at={token.expires_at}, now={now})"
        )

        response = httpx.post(
            STRAVA_TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": token.refresh_token,
            },
            timeout=15,
        )
        response.raise_for_status()
        new_data = response.json()

        token.access_token = new_data["access_token"]
        token.refresh_token = new_data["refresh_token"]
        token.expires_at = new_data["expires_at"]
        token.updated_at = datetime.utcnow()
        self.session.add(token)
        self.session.commit()
        self.session.refresh(token)
        return token

    def disconnect(self, user_id: int) -> None:
        """
        Revoke Strava access and delete the stored token for a user.

        Calls Strava's deauthorize endpoint first so the token is invalidated
        on Strava's side (required by the API agreement), then deletes the
        local token record regardless of whether the remote call succeeds.
        """
        token = self.get_token(user_id)
        if not token:
            return

        # Best-effort revocation on Strava's side — do not block on failure
        try:
            refreshed = self.refresh_if_needed(token)
            httpx.post(
                "https://www.strava.com/oauth/deauthorize",
                params={"access_token": refreshed.access_token},
                timeout=10,
            )
        except Exception as e:
            logger.warning(
                f"Strava deauthorize request failed for user_id={user_id}: {e}"
            )

        self.session.delete(token)
        self.session.commit()

    # ------------------------------------------------------------------
    # Athlete profile import
    # ------------------------------------------------------------------

    def fetch_athlete(self, access_token: str) -> Dict[str, Any]:
        """GET /athlete — returns the DetailedAthlete dict."""
        response = httpx.get(
            f"{STRAVA_API_BASE}/athlete",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def fetch_athlete_zones(self, access_token: str) -> Dict[str, Any]:
        """GET /athlete/zones — returns HR and power zone boundaries."""
        response = httpx.get(
            f"{STRAVA_API_BASE}/athlete/zones",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()

    def merge_athlete_profile(self, user_id: int, access_token: str) -> None:
        """
        Fetch athlete data from Strava and merge into RunnerProfile.
        Merge rules:
        - gender: only set if current value is 'unknown' or None
        - weight_kg: always update (factual, changes over time)
        - ftp: always update (no wizard field; Strava is authoritative)
        - birthday: always update from Strava (YYYY-MM-DD); also update age
        If GET /athlete/zones returns custom_zones=True, import HR zone boundaries.
        """
        import json
        from datetime import date as date_type

        profile = self.session.exec(
            select(RunnerProfile).where(RunnerProfile.user_id == user_id)
        ).first()
        if not profile:
            return

        try:
            athlete = self.fetch_athlete(access_token)
        except Exception as e:
            logger.warning(f"Could not fetch Strava athlete for user {user_id}: {e}")
            return

        changed = False

        # gender — only if not manually set
        sex = athlete.get("sex")
        if sex and (not profile.gender or profile.gender == "unknown"):
            profile.gender = "male" if sex == "M" else "female"
            changed = True

        # weight_kg — always update
        weight = athlete.get("weight")
        if weight:
            profile.weight_kg = float(weight)
            changed = True

        # ftp — always update
        ftp = athlete.get("ftp")
        if ftp:
            profile.ftp = int(ftp)
            changed = True

        # birthday — always update; recompute age from it
        birthday_str = athlete.get("birthday")  # "YYYY-MM-DD" or None
        if birthday_str:
            try:
                bday = date_type.fromisoformat(birthday_str)
                profile.birthday = bday
                today = date_type.today()
                age = (
                    today.year
                    - bday.year
                    - ((today.month, today.day) < (bday.month, bday.day))
                )
                profile.age = age
                changed = True
            except ValueError:
                logger.warning(
                    f"Strava returned unparseable birthday '{birthday_str}' for user {user_id}"
                )

        if changed:
            self.session.add(profile)
            self.session.commit()

        # HR zone boundaries — import if athlete has custom zones set
        try:
            zones_data = self.fetch_athlete_zones(access_token)
            hr_zones = zones_data.get("heart_rate", {})
            if hr_zones.get("custom_zones") and not profile.training_zones_json:
                # Convert Strava zones to our zone schema
                strava_zone_list = hr_zones.get("zones", [])
                if strava_zone_list:
                    converted = [
                        {
                            "zone": idx + 1,
                            "name": z.get("name", f"Zone {idx + 1}"),
                            "minBpm": z.get("min", 0),
                            "maxBpm": z.get("max", 0),
                        }
                        for idx, z in enumerate(strava_zone_list)
                    ]
                    profile.training_zones_json = json.dumps({"hr": converted})
                    self.session.add(profile)
                    self.session.commit()
        except Exception as e:
            logger.warning(f"Could not import Strava HR zones for user {user_id}: {e}")

    # ------------------------------------------------------------------
    # Activity fetching and mapping
    # ------------------------------------------------------------------

    def fetch_activities(
        self, access_token: str, start_date: date, end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Paginate GET /athlete/activities with after/before epoch params.
        Returns list of raw Strava activity summary dicts.
        """
        after = int(
            datetime(start_date.year, start_date.month, start_date.day).timestamp()
        )
        before = int(
            datetime(
                end_date.year, end_date.month, end_date.day, 23, 59, 59
            ).timestamp()
        )

        results = []
        page = 1
        per_page = 100

        while True:
            response = httpx.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "after": after,
                    "before": before,
                    "page": page,
                    "per_page": per_page,
                },
                timeout=30,
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            results.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        return results

    def fetch_activity_laps(
        self, access_token: str, activity_id: int
    ) -> List[Dict[str, Any]]:
        """GET /activities/{id}/laps"""
        try:
            response = httpx.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}/laps",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(
                f"Could not fetch laps for Strava activity {activity_id}: {e}"
            )
            return []

    def fetch_activity_zones(
        self, access_token: str, activity_id: int
    ) -> List[Dict[str, Any]]:
        """
        GET /activities/{id}/zones — Summit only.
        Returns empty list for free users.
        """
        try:
            response = httpx.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}/zones",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(
                f"Could not fetch zones for Strava activity {activity_id}: {e}"
            )
            return []

    def fetch_activity_streams(
        self, access_token: str, activity_id: int
    ) -> Dict[str, Any]:
        """
        GET /activities/{id}/streams?keys=time,heartrate,velocity_smooth,watts
        Returns dict of stream data keyed by type.
        """
        try:
            response = httpx.get(
                f"{STRAVA_API_BASE}/activities/{activity_id}/streams",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"keys": "time,heartrate,velocity_smooth,watts"},
                timeout=30,
            )
            response.raise_for_status()
            raw = response.json()
            # Convert from list of {type, data} to {type: data}
            return {item["type"]: item["data"] for item in raw if "type" in item}
        except Exception as e:
            logger.debug(
                f"Could not fetch streams for Strava activity {activity_id}: {e}"
            )
            return {}

    def compute_zones_from_streams(
        self,
        streams: Dict[str, Any],
        hr_thresholds: List[Dict],
        pace_thresholds: List[Dict],
        power_thresholds: List[Dict],
    ):
        """
        Derive time-in-zone distributions from raw Strava stream data.
        Uses same bucketing logic as GarminService.enrich_zones_with_telemetry.

        Returns (hr_zones, pace_zones, power_zones) as lists of zone dicts.
        """
        time_data = streams.get("time", [])
        hr_data = streams.get("heartrate", [])
        velocity_data = streams.get("velocity_smooth", [])
        watts_data = streams.get("watts", [])

        if not time_data:
            return [], [], []

        def build_buckets(thresholds, low_key, zone_key):
            buckets = {}
            sorted_t = sorted(thresholds, key=lambda x: x[low_key])
            for i, t in enumerate(sorted_t):
                z = t[zone_key]
                high = sorted_t[i + 1][low_key] if i + 1 < len(sorted_t) else 99999.0
                buckets[z] = {
                    "low": t[low_key],
                    "high": high,
                    "secs": 0.0,
                }
            return buckets

        hr_buckets = (
            build_buckets(hr_thresholds, "minBpm", "zone") if hr_thresholds else {}
        )
        pace_buckets = (
            build_buckets(pace_thresholds, "lowBoundary_m_s", "zone")
            if pace_thresholds
            else {}
        )
        power_buckets = (
            build_buckets(power_thresholds, "lowBoundary", "zone")
            if power_thresholds
            else {}
        )

        n = len(time_data)
        for i in range(n):
            dt = (time_data[i] - time_data[i - 1]) if i > 0 else 0.0
            if dt <= 0:
                continue

            # HR
            if hr_buckets and i < len(hr_data) and hr_data[i] is not None:
                val = hr_data[i]
                for z, b in sorted(hr_buckets.items(), reverse=True):
                    if val >= b["low"]:
                        b["secs"] += dt
                        break

            # Pace (velocity_smooth is in m/s)
            if pace_buckets and i < len(velocity_data) and velocity_data[i] is not None:
                val = velocity_data[i]
                for z, b in sorted(pace_buckets.items(), reverse=True):
                    if val >= b["low"]:
                        b["secs"] += dt
                        break

            # Power
            if power_buckets and i < len(watts_data) and watts_data[i] is not None:
                val = watts_data[i]
                for z, b in sorted(power_buckets.items(), reverse=True):
                    if val >= b["low"]:
                        b["secs"] += dt
                        break

        total_secs = time_data[-1] if time_data else 1.0

        def finalize(buckets):
            return [
                {
                    "zoneNumber": z,
                    "secsInZone": round(b["secs"], 3),
                    "zoneLow": b["low"],
                    "zoneHigh": b["high"],
                    "percentInZone": round(b["secs"] / total_secs * 100, 2)
                    if total_secs > 0
                    else 0,
                }
                for z, b in sorted(buckets.items())
            ]

        return finalize(hr_buckets), finalize(pace_buckets), finalize(power_buckets)

    def map_activity(
        self,
        raw: Dict[str, Any],
        laps: List[Dict[str, Any]],
        hr_zones: List[Dict],
        pace_zones: List[Dict],
        power_zones: List[Dict],
    ) -> ActivitySchema:
        """Map a raw Strava activity summary + enrichment data to ActivitySchema."""
        sport_type = raw.get("sport_type", raw.get("type", "Run"))
        internal_type = _SPORT_TYPE_MAP.get(sport_type, sport_type.lower())

        start_local = raw.get("start_date_local", "")
        act_date = start_local[:10] if start_local else ""

        return ActivitySchema(
            date=act_date,
            name=raw.get("name", "Strava Activity"),
            type=internal_type,
            distance_m=float(raw.get("distance", 0)),
            duration_s=float(raw.get("elapsed_time", 0)),
            activityId=None,
            stravaActivityId=raw.get("id"),
            source="strava",
            average_pace_m_s=raw.get("average_speed"),
            average_hr=raw.get("average_heartrate"),
            max_hr=raw.get("max_heartrate"),
            average_power=raw.get("average_watts"),
            aerobic_te=None,
            anaerobic_te=None,
            training_load=raw.get("suffer_score"),
            calories=raw.get("calories"),
            hr_zones=hr_zones,
            pace_zones=pace_zones,
            power_zones=power_zones,
            splits=laps,
        )

    # ------------------------------------------------------------------
    # High-level sync
    # ------------------------------------------------------------------

    def handle_webhook_event(self, event: Dict[str, Any]) -> None:
        """
        Handle a Strava webhook event.
        - Deauthorization: Deletes token
        - Activity update/create: Triggers sync
        """
        object_type = event.get("object_type")
        aspect_type = event.get("aspect_type")
        owner_id = event.get("owner_id")

        logger.info(
            f"Strava webhook: object_type={object_type} aspect_type={aspect_type} owner_id={owner_id}"
        )

        updates = event.get("updates", {})
        if (
            object_type == "athlete"
            and aspect_type == "update"
            and updates.get("authorized") == "false"
        ):
            if owner_id:
                token = self.session.exec(
                    select(StravaToken).where(StravaToken.athlete_id == owner_id)
                ).first()
                if token:
                    self.session.delete(token)
                    self.session.commit()
                    logger.info(
                        f"Deleted Strava token for athlete_id={owner_id} (deauthorized via webhook)"
                    )
            return

        if object_type == "activity" and aspect_type in ("create", "update"):
            if owner_id:
                token = self.session.exec(
                    select(StravaToken).where(StravaToken.athlete_id == owner_id)
                ).first()
                if token:
                    try:
                        user = self.session.exec(
                            select(User).where(User.id == token.user_id)
                        ).first()
                        if user:
                            # Local imports to prevent circular imports
                            from app.services.activities import ActivityService
                            from app.services.plans import PlanService

                            activities = self.sync_activities(user=user, days=2)
                            activity_service = ActivityService(self.session)
                            activity_service.save_activities(activities, user=user)

                            plan_service = PlanService(self.session)
                            plan_service.recalculate_plan_progression(user)
                    except Exception as e:
                        logger.warning(
                            f"Webhook-triggered sync failed for athlete_id={owner_id}: {e}"
                        )
            return

    def sync_activities(
        self,
        user: User,
        days: int = 7,
        hr_thresholds: List[Dict] = None,
        pace_thresholds: List[Dict] = None,
        power_thresholds: List[Dict] = None,
    ) -> List[ActivitySchema]:
        """
        Fetch and enrich Strava activities for the past N days.
        Returns list of ActivitySchema ready for ActivityService.save_activities.

        Zone computation strategy:
        1. For each activity, try GET /activities/{id}/zones (Summit users).
        2. If empty, fall back to Streams API (for activities within streams_max_age_days).
        3. If streams not available, zones remain empty.
        """
        token = self.get_token(user.id)
        if not token:
            raise ValueError("Strava not connected for this user")

        token = self.refresh_if_needed(token)

        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        streams_cutoff = end_date - timedelta(days=self.streams_max_age_days)

        raw_activities = self.fetch_activities(token.access_token, start_date, end_date)
        results: List[ActivitySchema] = []

        for raw in raw_activities:
            activity_id = raw.get("id")
            if not activity_id:
                continue

            laps = self.fetch_activity_laps(token.access_token, activity_id)

            hr_zones_out: List[Dict] = []
            pace_zones_out: List[Dict] = []
            power_zones_out: List[Dict] = []

            # Try Summit zones first
            zones_raw = self.fetch_activity_zones(token.access_token, activity_id)
            if zones_raw:
                for zone_set in zones_raw:
                    zone_type = zone_set.get("type")
                    distribution = zone_set.get("distribution_buckets", [])
                    # Strava includes a leading bucket with min=-1 for "below all zones".
                    # Filter it out so zone numbers start at 1 and match standard Z1-Z5.
                    valid_buckets = [b for b in distribution if b.get("min", 0) >= 0]
                    if zone_type == "heartrate":
                        hr_zones_out = [
                            {
                                "zoneNumber": i + 1,
                                "secsInZone": b.get("time", 0),
                                "zoneLow": b.get("min", 0),
                                "zoneHigh": b.get("max", 0),
                                "percentInZone": 0,
                            }
                            for i, b in enumerate(valid_buckets)
                        ]
                    elif zone_type == "power":
                        power_zones_out = [
                            {
                                "zoneNumber": i + 1,
                                "secsInZone": b.get("time", 0),
                                "zoneLow": b.get("min", 0),
                                "zoneHigh": b.get("max", 0),
                                "percentInZone": 0,
                            }
                            for i, b in enumerate(valid_buckets)
                        ]
            else:
                # Fall back to streams for recent activities
                start_local = raw.get("start_date_local", "")
                act_date_str = start_local[:10] if start_local else ""
                try:
                    act_date_val = date.fromisoformat(act_date_str)
                    within_age = act_date_val >= streams_cutoff
                except ValueError:
                    within_age = False

                if within_age and (
                    hr_thresholds or pace_thresholds or power_thresholds
                ):
                    streams = self.fetch_activity_streams(
                        token.access_token, activity_id
                    )
                    if streams:
                        hr_zones_out, pace_zones_out, power_zones_out = (
                            self.compute_zones_from_streams(
                                streams,
                                hr_thresholds or [],
                                pace_thresholds or [],
                                power_thresholds or [],
                            )
                        )

            activity_schema = self.map_activity(
                raw, laps, hr_zones_out, pace_zones_out, power_zones_out
            )
            results.append(activity_schema)

        return results
