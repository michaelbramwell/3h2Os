"""
Zone calculator for auto-generating training zones from athlete profile data.

Uses standard, evidence-based formulas:
- Max HR: 220 - age (Haskell/Fox) or 208 - (0.7 * age) (Tanaka)
- HR zones: Percentage of max HR (Karvonen method not used as it requires resting HR)
- Pace zones: Derived from event distance and target/estimated finish time
- Swim CSS (Critical Swim Speed): Estimated from age and experience level

All calculations use generic sports science principles, no proprietary methodology.
"""

import json
import logging
from datetime import date
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def calculate_max_hr(age: int) -> int:
    """Estimate max heart rate using Tanaka formula (more accurate than 220-age)."""
    return round(208 - (0.7 * age))


def calculate_hr_zones(age: int) -> List[Dict[str, Any]]:
    """
    Calculate 5 heart rate training zones based on percentage of max HR.

    Zone 1: Recovery (50-60% max HR)
    Zone 2: Aerobic / Easy (60-70% max HR)
    Zone 3: Tempo (70-80% max HR)
    Zone 4: Threshold (80-90% max HR)
    Zone 5: VO2max (90-100% max HR)
    """
    max_hr = calculate_max_hr(age)

    zone_boundaries = [
        (1, 0.50, 0.60, "Recovery"),
        (2, 0.60, 0.70, "Aerobic"),
        (3, 0.70, 0.80, "Tempo"),
        (4, 0.80, 0.90, "Threshold"),
        (5, 0.90, 1.00, "VO2max"),
    ]

    zones = []
    for zone_num, low_pct, high_pct, desc in zone_boundaries:
        zones.append(
            {
                "zone": zone_num,
                "lowBoundary_bpm": round(max_hr * low_pct),
                "highBoundary_bpm": round(max_hr * high_pct),
                "description": desc,
            }
        )

    return zones


def estimate_easy_pace_m_s(experience_level: str, event_type: str) -> float:
    """
    Estimate an easy running pace in m/s based on experience level.
    These are conservative estimates for plan generation.
    """
    # Base easy paces (min/km converted to m/s)
    # Beginner: ~7:00/km, Intermediate: ~5:45/km, Advanced: ~4:45/km
    base_paces = {
        "beginner": 1000 / (7.0 * 60),  # ~2.38 m/s
        "intermediate": 1000 / (5.75 * 60),  # ~2.90 m/s
        "advanced": 1000 / (4.75 * 60),  # ~3.51 m/s
    }
    return base_paces.get(experience_level, base_paces["intermediate"])


def calculate_pace_zones(
    experience_level: str,
    event_type: str,
    target_time: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate running pace zones in m/s.

    When a target_time is provided and the event distance is known, zones are
    derived directly from race pace using standard training-zone fractions
    (Jack Daniels / Pfitzinger conventions):

      Zone 1: Recovery  — race_pace * 0.70  (~E-pace lower bound)
      Zone 2: Easy      — race_pace * 0.75  (~E-pace)
      Zone 3: Tempo     — race_pace * 0.96  (~marathon/M-pace)
      Zone 4: Threshold — race_pace * 1.05  (~T-pace, ~1-hour race pace)
      Zone 5: VO2 Max   — race_pace * 1.14  (~I-pace)

    Without a target time the zones fall back to experience-level estimates
    using the same multipliers anchored off the estimated easy pace.
    """
    from app.models.domain import EVENT_DISTANCES_M, EventType as ET

    easy_pace = estimate_easy_pace_m_s(experience_level, event_type)
    race_pace: Optional[float] = None

    # If we have a target time and can map the event to a distance, derive
    # zones from race pace directly for much better accuracy.
    if target_time:
        try:
            et = ET(event_type)
            distance_m = EVENT_DISTANCES_M.get(et)
            if distance_m:
                parts = target_time.split(":")
                if len(parts) == 3:
                    total_seconds = (
                        int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    )
                elif len(parts) == 2:
                    total_seconds = int(parts[0]) * 60 + int(parts[1])
                else:
                    total_seconds = None

                if total_seconds and total_seconds > 0:
                    race_pace = distance_m / total_seconds
                    easy_pace = race_pace * 0.75
        except (ValueError, KeyError):
            pass  # Invalid target_time format -- fall back to experience-level estimate

    if race_pace is not None:
        # Race-pace-anchored zones (accurate when target time is known)
        zones = [
            {
                "zone": 1,
                "lowBoundary_m_s": round(race_pace * 0.70, 3),
                "description": "Recovery",
            },
            {
                "zone": 2,
                "lowBoundary_m_s": round(race_pace * 0.75, 3),
                "description": "Easy",
            },
            {
                "zone": 3,
                "lowBoundary_m_s": round(race_pace * 0.96, 3),
                "description": "Tempo",
            },
            {
                "zone": 4,
                "lowBoundary_m_s": round(race_pace * 1.05, 3),
                "description": "Threshold",
            },
            {
                "zone": 5,
                "lowBoundary_m_s": round(race_pace * 1.14, 3),
                "description": "Interval",
            },
        ]
    else:
        # Fallback: experience-level-anchored zones
        zones = [
            {
                "zone": 1,
                "lowBoundary_m_s": round(easy_pace * 0.80, 3),
                "description": "Recovery",
            },
            {
                "zone": 2,
                "lowBoundary_m_s": round(easy_pace, 3),
                "description": "Easy",
            },
            {
                "zone": 3,
                "lowBoundary_m_s": round(easy_pace * 1.15, 3),
                "description": "Tempo",
            },
            {
                "zone": 4,
                "lowBoundary_m_s": round(easy_pace * 1.25, 3),
                "description": "Threshold",
            },
            {
                "zone": 5,
                "lowBoundary_m_s": round(easy_pace * 1.40, 3),
                "description": "Interval",
            },
        ]

    return zones


def calculate_swim_pace_zones(
    experience_level: str,
) -> List[Dict[str, Any]]:
    """
    Calculate swimming pace zones in m/s based on estimated CSS.

    CSS estimates (per 100m):
    Beginner: ~2:30/100m, Intermediate: ~1:50/100m, Advanced: ~1:25/100m
    """
    css_paces = {
        "beginner": 100 / 150,  # 2:30/100m = ~0.667 m/s
        "intermediate": 100 / 110,  # 1:50/100m = ~0.909 m/s
        "advanced": 100 / 85,  # 1:25/100m = ~1.176 m/s
    }
    css = css_paces.get(experience_level, css_paces["intermediate"])

    zones = [
        {"zone": 1, "lowBoundary_m_s": round(css * 0.75, 3), "description": "Recovery"},
        {
            "zone": 2,
            "lowBoundary_m_s": round(css * 0.85, 3),
            "description": "Endurance",
        },
        {"zone": 3, "lowBoundary_m_s": round(css, 3), "description": "CSS / Tempo"},
        {
            "zone": 4,
            "lowBoundary_m_s": round(css * 1.05, 3),
            "description": "Threshold",
        },
        {"zone": 5, "lowBoundary_m_s": round(css * 1.15, 3), "description": "VO2max"},
    ]

    return zones


def calculate_zones(
    age: int,
    experience_level: str,
    sport: str,
    event_type: str,
    target_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calculate all training zones for a given athlete profile.

    Returns a dict with keys: heartRate, pace (running) or swimPace (swimming).
    """
    zones: Dict[str, Any] = {}

    zones["heartRate"] = calculate_hr_zones(age)

    if sport == "running":
        zones["pace"] = calculate_pace_zones(experience_level, event_type, target_time)
    elif sport == "swimming":
        zones["swimPace"] = calculate_swim_pace_zones(experience_level)
    else:
        # Default to running
        zones["pace"] = calculate_pace_zones(experience_level, event_type, target_time)

    return zones


def _pace_zones_from_lt_pace(lt_pace_m_s: float) -> List[Dict[str, Any]]:
    """
    Derive 5 running pace zones from a lactate-threshold pace (m/s).

    Fractions anchored at LT (Zone 4) using Jack Daniels / Pfitzinger speed ratios.
    All values are *speed* fractions (m/s), so a fraction < 1.0 means slower than LT.

    Verified against VDOT tables:
      Z1 Recovery  = lt_pace * 0.760  (~lower E-pace bound, ~25% slower than LT)
      Z2 Easy      = lt_pace * 0.835  (~E-pace, ~20% slower than LT)
      Z3 Tempo     = lt_pace * 0.915  (~M-pace, ~9% slower than LT)
      Z4 Threshold = lt_pace * 1.000  (LT pace itself)
      Z5 VO2 Max   = lt_pace * 1.090  (~I-pace, ~9% faster than LT)
    """
    return [
        {
            "zone": 1,
            "lowBoundary_m_s": round(lt_pace_m_s * 0.760, 3),
            "description": "Recovery",
        },
        {
            "zone": 2,
            "lowBoundary_m_s": round(lt_pace_m_s * 0.835, 3),
            "description": "Easy",
        },
        {
            "zone": 3,
            "lowBoundary_m_s": round(lt_pace_m_s * 0.915, 3),
            "description": "Tempo",
        },
        {
            "zone": 4,
            "lowBoundary_m_s": round(lt_pace_m_s * 1.000, 3),
            "description": "Threshold",
        },
        {
            "zone": 5,
            "lowBoundary_m_s": round(lt_pace_m_s * 1.090, 3),
            "description": "Interval",
        },
    ]


def _best_5k_lt_from_activities(user_id: int, session) -> Optional[float]:
    """
    Derive an LT pace (m/s) from the fastest near-5K activity in actualactivity.

    Scans all running activities between 4900m and 5200m and returns
    LT = best_5k_pace * 0.93 (Jack Daniels T-pace fraction).

    Returns None if no qualifying activities exist.
    """
    from sqlmodel import select as _select
    from app.core.database import ActualActivity

    rows = session.exec(
        _select(ActualActivity.average_pace_m_s)
        .where(ActualActivity.user_id == user_id)
        .where(
            ActualActivity.type.in_(
                ["Run", "running", "TrailRun", "run", "trail_running"]
            )
        )
        .where(ActualActivity.distance_m >= 4900)
        .where(ActualActivity.distance_m <= 5200)
        .where(ActualActivity.average_pace_m_s.isnot(None))
        .where(ActualActivity.average_pace_m_s > 0)
        .order_by(ActualActivity.average_pace_m_s.desc())
        .limit(1)
    ).first()

    if not rows:
        return None

    best_5k_pace_m_s = float(rows)
    derived_lt = round(best_5k_pace_m_s * 0.93, 4)
    logger.debug(
        f"Best 5K pace from activities: {best_5k_pace_m_s:.3f} m/s "
        f"→ LT {derived_lt:.3f} m/s (user_id={user_id})"
    )
    return derived_lt


def refresh_training_zones(profile, session) -> bool:
    """
    Recalculate and persist training_zones_json for *profile* using the best
    available data source, in priority order:

    For HR zones:
      1. Strava /athlete/zones  → custom or Strava-calculated HR zone boundaries
      2. Formula                → Tanaka age-based max HR formula

    For pace zones, the best available anchor is used:
      1. Garmin running zones   → pace zones fetched directly from Garmin Connect
                                   user-settings (profile.garmin_running_zones_json).
                                   These are the exact zones the user sees in Garmin/Strava.
      2. Best 5K from activities → fastest near-5K (4900–5200m) run in actualactivity,
                                   LT = 5K pace * 0.93 (Jack Daniels T-pace).
                                   Most reliable signal — always uses the fastest effort
                                   on record regardless of source (Garmin or Strava).
      3. Garmin LT pace         → device-measured lactate threshold (m/s) stored on profile.
                                   Used only when no 5K efforts exist in the activity log.
      4. Project target_time    → race-pace-anchored zones from user's goal time.
      5. Experience level       → coarse 3-tier fallback (beginner/intermediate/advanced).

    Returns True if training_zones_json was updated, False otherwise.
    """
    from sqlmodel import select as _select
    from app.core.database import StravaToken, RunnerProject

    if not profile:
        return False

    try:
        # ------------------------------------------------------------------
        # Supporting data
        # ------------------------------------------------------------------
        project = session.exec(
            _select(RunnerProject).where(RunnerProject.user_id == profile.user_id)
        ).first()
        event_type = (project.event_type or "marathon") if project else "marathon"
        target_time = project.target_time if project else None
        experience_level = profile.experience_level or "intermediate"

        # ------------------------------------------------------------------
        # HR zones: Strava if connected, else formula
        # ------------------------------------------------------------------
        strava_token = session.exec(
            _select(StravaToken).where(StravaToken.user_id == profile.user_id)
        ).first()

        hr_zones: List[Dict[str, Any]] = []
        if strava_token:
            try:
                from app.services.strava import StravaService

                svc = StravaService(session)
                token = svc.refresh_if_needed(strava_token)
                zones_data = svc.fetch_athlete_zones(token.access_token)
                strava_zone_list = zones_data.get("heart_rate", {}).get("zones", [])
                if strava_zone_list:
                    hr_zones = [
                        {
                            "zone": idx + 1,
                            "lowBoundary_bpm": z.get("min", 0),
                            "highBoundary_bpm": z.get("max", 0),
                            "description": z.get("name", f"Zone {idx + 1}"),
                        }
                        for idx, z in enumerate(strava_zone_list)
                    ]
            except Exception as e:
                logger.warning(f"Could not fetch Strava HR zones for refresh: {e}")

        if not hr_zones:
            age = profile.age
            if age is None and profile.birthday:
                age = (date.today() - profile.birthday).days // 365
            if age is None:
                age = 30  # Default fallback
            hr_zones = calculate_hr_zones(age)

        # ------------------------------------------------------------------
        # Pace zones — priority ladder
        # ------------------------------------------------------------------
        pace_zones: Optional[List[Dict[str, Any]]] = None

        # Priority 1: Garmin running zones (direct from Garmin Connect settings)
        if profile.garmin_running_zones_json:
            try:
                garmin_zones = json.loads(profile.garmin_running_zones_json)
                if (
                    garmin_zones
                    and isinstance(garmin_zones, list)
                    and len(garmin_zones) >= 3
                ):
                    pace_zones = garmin_zones
                    logger.info(
                        f"Training zones refreshed via Garmin running zones for user_id={profile.user_id}"
                    )
            except Exception:
                pass

        # Priority 2: Best 5K from activity log (most reliable — always uses fastest effort)
        if pace_zones is None:
            lt_from_5k = _best_5k_lt_from_activities(profile.user_id, session)
            if lt_from_5k:
                pace_zones = _pace_zones_from_lt_pace(lt_from_5k)
                logger.info(
                    f"Training zones refreshed via best 5K activity (LT={lt_from_5k:.3f} m/s) "
                    f"for user_id={profile.user_id}"
                )

        # Priority 3: Garmin device LT pace (fallback when no 5K efforts on record)
        if (
            pace_zones is None
            and profile.lactate_threshold_pace
            and profile.lactate_threshold_pace > 0
        ):
            pace_zones = _pace_zones_from_lt_pace(profile.lactate_threshold_pace)
            logger.info(
                f"Training zones refreshed via Garmin LT pace for user_id={profile.user_id}"
            )

        # Priority 4 & 5: target_time / experience level fallback
        if pace_zones is None:
            pace_zones = calculate_pace_zones(experience_level, event_type, target_time)
            logger.info(
                f"Training zones refreshed via defaults for user_id={profile.user_id}"
            )

        zones_dict: Dict[str, Any] = {"heartRate": hr_zones, "pace": pace_zones}
        profile.training_zones_json = json.dumps(zones_dict)
        session.add(profile)
        session.commit()
        return True

    except Exception as e:
        logger.error(
            f"refresh_training_zones failed for user_id={profile.user_id}: {e}"
        )
        return False
