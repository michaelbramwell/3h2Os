"""
Base template logic shared across running and swimming plans.

Handles:
- Phase structure calculation (how many weeks per phase given total weeks)
- Volume curve generation (weekly target volumes)
- Workout distribution across days
- Plan skeleton generation from a template definition
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import math

from app.models.domain import EventType, EVENT_DISTANCES_M


@dataclass
class PhaseDefinition:
    """Defines a training phase within a plan."""

    name: str  # "base", "build", "peak", "taper", "race"
    description: str
    volume_factor: float  # Multiplier of peak volume (e.g. 0.6 for base start)
    intensity_ratio: float  # Fraction of volume that's high intensity (0.0-0.25)
    includes_stepback: bool = True  # Whether to insert recovery weeks


@dataclass
class SessionTemplate:
    """Template for a single workout session."""

    name_pattern: (
        str  # e.g. "{distance}k Easy Run" -- {distance} replaced at generation
    )
    activity_type: str  # ActivityType value: "Run", "Swimming", etc.
    workout_format: str  # WorkoutFormat value: "Easy", "Tempo", etc.
    volume_share: float  # Fraction of weekly volume this session takes (e.g. 0.15)
    description_pattern: Optional[str] = None  # Optional description template
    time_of_day: str = "AM"


@dataclass
class WeekTemplate:
    """Template for a week's worth of sessions."""

    sessions: List[Tuple[int, SessionTemplate]]  # (day_index 0=Mon, template)


@dataclass
class PlanTemplateDefinition:
    """Complete template definition for a plan type."""

    sport: str
    event_type: str
    level: str
    default_weeks: int
    phases: List[PhaseDefinition]
    # Phase proportions as fractions of total weeks (must sum to ~1.0)
    phase_proportions: List[float]
    # Different week templates for different phases
    # Key: phase name, value: WeekTemplate or list of WeekTemplates.
    # When a list is provided, templates are distributed across the weeks
    # of that phase (first template for early weeks, last for final weeks).
    week_templates: Dict[str, Union[WeekTemplate, List[WeekTemplate]]]
    # Peak weekly volume in metres for this template
    peak_volume_m: float
    # Step-back frequency: insert recovery week every N build weeks
    stepback_frequency: int = 3
    stepback_factor: float = 0.65


def calculate_phase_structure(
    total_weeks: int,
    phases: List[PhaseDefinition],
    phase_proportions: List[float],
) -> List[Dict[str, Any]]:
    """
    Calculate how many weeks each phase gets given total plan length.

    Returns list of {"name": str, "weeks": int, "description": str, "volume_factor": float}.
    """
    # Allocate weeks proportionally, ensuring at least 1 week per phase
    raw_allocations = [max(1, round(total_weeks * p)) for p in phase_proportions]

    # Adjust to match total_weeks exactly
    diff = total_weeks - sum(raw_allocations)
    if diff != 0:
        # Add/remove from the largest phase (usually "build")
        largest_idx = raw_allocations.index(max(raw_allocations))
        raw_allocations[largest_idx] += diff

    result = []
    for phase, weeks in zip(phases, raw_allocations):
        result.append(
            {
                "name": phase.name,
                "weeks": weeks,
                "description": phase.description,
                "volume_factor": phase.volume_factor,
                "intensity_ratio": phase.intensity_ratio,
                "includes_stepback": phase.includes_stepback,
            }
        )

    return result


def _apply_taper_weeks_override(
    phase_structure: List[Dict[str, Any]],
    taper_weeks_override: int,
) -> None:
    """
    Adjust the taper phase in phase_structure to the exact number of weeks
    specified. The difference is redistributed to the build phase (or the
    largest non-taper phase as fallback). Mutates phase_structure in place.
    """
    taper_idx = next(
        (i for i, p in enumerate(phase_structure) if p["name"] == "taper"),
        None,
    )
    if taper_idx is None:
        return

    current_taper = phase_structure[taper_idx]["weeks"]
    diff = current_taper - taper_weeks_override
    if diff == 0:
        return

    phase_structure[taper_idx]["weeks"] = taper_weeks_override

    # Redistribute the difference to the build phase
    build_idx = next(
        (i for i, p in enumerate(phase_structure) if p["name"] == "build"),
        None,
    )
    if build_idx is not None:
        phase_structure[build_idx]["weeks"] += diff
    else:
        # Fallback: add to the largest non-taper phase
        largest_idx = max(
            (i for i in range(len(phase_structure)) if i != taper_idx),
            key=lambda i: phase_structure[i]["weeks"],
        )
        phase_structure[largest_idx]["weeks"] += diff


def _calculate_weekly_volumes(
    phase_structure: List[Dict[str, Any]],
    peak_volume_m: float,
    stepback_frequency: int = 3,
    stepback_factor: float = 0.65,
) -> List[Tuple[float, str, str]]:
    """
    Calculate target volume for each week across all phases.

    Returns list of (volume_m, phase_name, week_status) tuples.
    """
    weekly_data = []

    for phase in phase_structure:
        phase_name = phase["name"]
        num_weeks = phase["weeks"]
        volume_factor = phase["volume_factor"]
        includes_stepback = phase["includes_stepback"]

        if phase_name == "base":
            # Linear ramp from volume_factor to ~0.75 of peak
            start_vol = peak_volume_m * volume_factor
            end_vol = peak_volume_m * 0.75
            build_count = 0
            for i in range(num_weeks):
                progress = i / max(1, num_weeks - 1)
                vol = start_vol + (end_vol - start_vol) * progress

                if includes_stepback and build_count >= stepback_frequency:
                    vol = vol * stepback_factor
                    weekly_data.append((vol, phase_name, "recovery"))
                    build_count = 0
                else:
                    weekly_data.append((vol, phase_name, "normal"))
                    build_count += 1

        elif phase_name == "build":
            # Progressive overload: 7% per build week, with stepbacks
            if weekly_data:
                base_vol = weekly_data[-1][0]
                # If last week was recovery, use the one before
                if weekly_data[-1][2] == "recovery" and len(weekly_data) > 1:
                    base_vol = weekly_data[-2][0]
            else:
                base_vol = peak_volume_m * volume_factor

            current_vol = base_vol
            build_count = 0
            for i in range(num_weeks):
                if includes_stepback and build_count >= stepback_frequency:
                    vol = current_vol * stepback_factor
                    weekly_data.append((vol, phase_name, "recovery"))
                    build_count = 0
                else:
                    current_vol *= 1.07
                    current_vol = min(current_vol, peak_volume_m)
                    weekly_data.append((current_vol, phase_name, "normal"))
                    build_count += 1

        elif phase_name == "peak":
            # Maintain near-peak volume with higher intensity
            for i in range(num_weeks):
                vol = peak_volume_m * volume_factor
                weekly_data.append((vol, phase_name, "normal"))

        elif phase_name == "taper":
            # Progressive volume reduction
            if weekly_data:
                start_vol = weekly_data[-1][0]
            else:
                start_vol = peak_volume_m

            for i in range(num_weeks):
                # Reduce by ~20% each taper week
                progress = (i + 1) / num_weeks
                vol = start_vol * (1 - progress * 0.4)
                weekly_data.append((vol, phase_name, "taper"))

        elif phase_name == "race":
            # Race week: minimal volume
            vol = peak_volume_m * volume_factor
            for i in range(num_weeks):
                weekly_data.append((vol, phase_name, "race"))

    return weekly_data


def _round_distance(distance_m: float) -> float:
    """Round distance to nearest 500m for cleanliness."""
    return round(distance_m / 500) * 500


def _format_distance_name(distance_m: float) -> str:
    """Format distance in km for workout names."""
    km = distance_m / 1000
    if km == int(km):
        return f"{int(km)}k"
    return f"{km:.1f}k"


def _remap_sessions_to_preferred_days(
    selected_sessions: List[Tuple[int, "SessionTemplate"]],
    preferred_training_days: Optional[List[int]],
    preferred_long_run_day: Optional[int],
) -> List[Tuple[int, "SessionTemplate"]]:
    """
    Remap session day indices to match user-preferred training days.

    Strategy:
    - Identify the long run session (Long or Progression format).
    - If preferred_long_run_day is set, place the long run on that day.
    - If preferred_training_days is set, distribute remaining sessions across
      those days in the same relative order they appear in the template.
    - The long run day is excluded from remaining slots to avoid doubling up.

    Returns a new list of (day_idx, SessionTemplate) tuples with remapped days.
    """
    if preferred_training_days is None and preferred_long_run_day is None:
        return selected_sessions

    # Separate long run from other sessions
    long_run_formats = {"Long", "Progression"}
    long_run = None
    other_sessions = []
    for day_idx, tmpl in selected_sessions:
        if tmpl.workout_format in long_run_formats and long_run is None:
            long_run = (day_idx, tmpl)
        else:
            other_sessions.append((day_idx, tmpl))

    # Sort other sessions by their original day index to preserve relative order
    other_sessions.sort(key=lambda s: s[0])

    # Determine the long run day
    if preferred_long_run_day is not None and long_run is not None:
        lr_day = preferred_long_run_day
    elif long_run is not None:
        lr_day = long_run[0]  # keep original
    else:
        lr_day = None

    # Build the list of available days for non-long-run sessions
    if preferred_training_days is not None:
        available_days = sorted(preferred_training_days)
        # Remove the long run day from available slots
        if lr_day is not None and lr_day in available_days:
            available_days = [d for d in available_days if d != lr_day]
    else:
        # No preferred days specified, but we may have a long run day override.
        # Keep original day indices for other sessions.
        result = list(other_sessions)
        if long_run is not None:
            result.append((lr_day, long_run[1]))
        return result

    # Assign other sessions to available days
    remapped = []
    for i, (_, tmpl) in enumerate(other_sessions):
        if i < len(available_days):
            remapped.append((available_days[i], tmpl))
        # If more sessions than available days, extra sessions are dropped
        # (the session_per_week cap should prevent this in practice)

    # Add the long run back
    if long_run is not None:
        remapped.append((lr_day, long_run[1]))

    return remapped


def generate_plan_from_template(
    template: "PlanTemplateDefinition",
    start_date: date,
    total_weeks: int,
    sessions_per_week: int,
    peak_volume_override: Optional[float] = None,
    event_type: Optional[str] = None,
    taper_weeks_override: Optional[int] = None,
    preferred_time_of_day: Optional[str] = None,
    preferred_training_days: Optional[List[int]] = None,
    preferred_long_run_day: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Generate a complete plan from a template definition.

    Returns a list of week dicts in the existing plan JSON format:
    [{"weekStarting": "2026-01-05", "status": "normal", "days": {...}}, ...]

    Args:
        taper_weeks_override: If set, overrides the taper phase length.
            The difference is redistributed to the build phase.
        preferred_time_of_day: If set ("AM" or "PM"), overrides the default
            time_of_day for all generated workouts.
        preferred_training_days: If set, remap sessions to these day indices
            (0=Mon..6=Sun).
        preferred_long_run_day: If set, place the long run on this day index.
    """
    peak_volume = peak_volume_override or template.peak_volume_m

    # Resolve the actual event distance for race day
    race_distance_m: Optional[float] = None
    et = event_type or template.event_type
    try:
        race_distance_m = EVENT_DISTANCES_M.get(EventType(et))
    except (ValueError, KeyError):
        pass

    # 1. Calculate phase structure
    phase_structure = calculate_phase_structure(
        total_weeks, template.phases, template.phase_proportions
    )

    # 1b. Apply taper_weeks_override if provided
    if taper_weeks_override is not None:
        _apply_taper_weeks_override(phase_structure, taper_weeks_override)

    # 2. Calculate weekly volumes
    weekly_volumes = _calculate_weekly_volumes(
        phase_structure,
        peak_volume,
        template.stepback_frequency,
        template.stepback_factor,
    )

    # 3. Generate week-by-week plan
    plan_weeks = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Track the week index within each phase for multi-template phases
    phase_week_counts: Dict[str, int] = {}
    # Pre-compute total weeks per phase for index-based template selection
    phase_total_weeks: Dict[str, int] = {}
    for ps in phase_structure:
        phase_total_weeks[ps["name"]] = ps["weeks"]

    for week_idx, (volume_m, phase_name, week_status) in enumerate(weekly_volumes):
        week_start = start_date + timedelta(weeks=week_idx)

        # Track which week we are within this phase
        week_in_phase = phase_week_counts.get(phase_name, 0)
        phase_week_counts[phase_name] = week_in_phase + 1

        # Select the right week template for this phase
        tmpl_or_list = template.week_templates.get(
            phase_name,
            template.week_templates.get(
                "build", list(template.week_templates.values())[0]
            ),
        )

        if isinstance(tmpl_or_list, list):
            # Distribute templates across weeks in the phase
            total_in_phase = phase_total_weeks.get(phase_name, 1)
            # Map week_in_phase to a template index proportionally
            tmpl_idx = int(week_in_phase / max(1, total_in_phase) * len(tmpl_or_list))
            tmpl_idx = min(tmpl_idx, len(tmpl_or_list) - 1)
            week_template = tmpl_or_list[tmpl_idx]
        else:
            week_template = tmpl_or_list

        # Filter sessions to match requested sessions_per_week
        available_sessions = sorted(
            week_template.sessions, key=lambda s: s[1].volume_share, reverse=True
        )
        selected_sessions = available_sessions[:sessions_per_week]

        # Remap sessions to preferred training days if specified
        selected_sessions = _remap_sessions_to_preferred_days(
            selected_sessions, preferred_training_days, preferred_long_run_day
        )

        # Normalise volume shares so they sum to 1.0
        total_share = sum(s[1].volume_share for s in selected_sessions)
        if total_share == 0:
            total_share = 1.0

        # Build days map
        days = {}
        for i, day_name in enumerate(day_names):
            day_date = week_start + timedelta(days=i)
            days[day_name] = {
                "date": day_date.strftime("%Y-%m-%d"),
                "workouts": [],
            }

        # Place sessions on their designated days
        for day_idx, session_tmpl in selected_sessions:
            # Clamp day_idx to valid range
            actual_day_idx = day_idx % 7
            day_name = day_names[actual_day_idx]
            day_date = week_start + timedelta(days=actual_day_idx)

            # Calculate this session's distance
            normalised_share = session_tmpl.volume_share / total_share
            session_distance = _round_distance(volume_m * normalised_share)

            # Race day: use actual event distance instead of volume curve
            if session_tmpl.workout_format == "Race" and race_distance_m:
                session_distance = race_distance_m

            # Minimum distance of 1000m for any real session
            if session_distance < 1000 and session_tmpl.workout_format not in (
                "Rest",
                "Race",
            ):
                session_distance = 1000

            distance_label = _format_distance_name(session_distance)

            time_of_day = preferred_time_of_day or session_tmpl.time_of_day

            workout = {
                "name": session_tmpl.name_pattern.replace("{distance}", distance_label),
                "type": session_tmpl.activity_type,
                "format": session_tmpl.workout_format,
                "distance_m": session_distance,
                "timeOfDay": time_of_day,
            }

            if session_tmpl.description_pattern:
                workout["description"] = session_tmpl.description_pattern.replace(
                    "{distance}", distance_label
                )

            days[day_name]["workouts"].append(workout)

        plan_weeks.append(
            {
                "weekStarting": week_start.strftime("%Y-%m-%d"),
                "status": week_status,
                "days": days,
            }
        )

    return plan_weeks


def get_preview_volumes(
    template: "PlanTemplateDefinition",
    total_weeks: int,
    peak_volume_override: Optional[float] = None,
    taper_weeks_override: Optional[int] = None,
) -> List[float]:
    """Get just the volume curve for preview without generating full plan."""
    peak_volume = peak_volume_override or template.peak_volume_m
    phase_structure = calculate_phase_structure(
        total_weeks, template.phases, template.phase_proportions
    )
    if taper_weeks_override is not None:
        _apply_taper_weeks_override(phase_structure, taper_weeks_override)
    weekly_data = _calculate_weekly_volumes(
        phase_structure,
        peak_volume,
        template.stepback_frequency,
        template.stepback_factor,
    )
    return [v[0] for v in weekly_data]
