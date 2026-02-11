"""
Zone calculator for auto-generating training zones from athlete profile data.

Uses standard, evidence-based formulas:
- Max HR: 220 - age (Haskell/Fox) or 208 - (0.7 * age) (Tanaka)
- HR zones: Percentage of max HR (Karvonen method not used as it requires resting HR)
- Pace zones: Derived from event distance and target/estimated finish time
- Swim CSS (Critical Swim Speed): Estimated from age and experience level

All calculations use generic sports science principles, no proprietary methodology.
"""

from typing import Dict, Any, List, Optional


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
    If target_time is provided and event distance is known, derives from that.
    Otherwise uses experience-level estimates.

    Zone 1: Recovery (easy + 20%)
    Zone 2: Easy
    Zone 3: Tempo (easy pace * 1.15)
    Zone 4: Threshold (easy pace * 1.25)
    Zone 5: Interval (easy pace * 1.40)
    """
    from app.models.domain import EVENT_DISTANCES_M, EventType as ET

    easy_pace = estimate_easy_pace_m_s(experience_level, event_type)

    # If we have a target time and can map the event to a distance, refine the estimate
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
                    # Easy pace is roughly 70-75% of race pace for marathon,
                    # but varies by distance. Use a simple factor.
                    easy_pace = race_pace * 0.75
        except (ValueError, KeyError):
            pass

    zones = [
        {
            "zone": 1,
            "lowBoundary_m_s": round(easy_pace * 0.80, 3),
            "description": "Recovery",
        },
        {"zone": 2, "lowBoundary_m_s": round(easy_pace, 3), "description": "Easy"},
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
