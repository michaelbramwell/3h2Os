from datetime import date, timedelta
from typing import List, Dict, Any, Tuple, Union
import re

from app.models.domain import (
    Week as DomainWeek,
    Day as DomainDay,
    Workout as DomainWorkout,
)
from app.schemas import WeekSchema


def construct_domain_workout(
    name: str, activity_type: str, distance_m: float, time_of_day: str
) -> DomainWorkout:
    """Creates a DomainWorkout object."""
    return DomainWorkout(
        name=name,
        type=activity_type,
        distance_m=distance_m,
        timeOfDay=time_of_day,
    )


def create_domain_week(
    week_start: date, status: str, workouts: List[Any]
) -> DomainWeek:
    """
    Converts a flat list of workout objects (DB or simplified) into a DomainWeek.
    'workouts' can be PlanWorkout DB objects or any object with:
    name, activity_type/type, distance_m, time_of_day, date
    """
    # Group by Day Name
    days_map = {k: [] for k in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}

    # Populate workouts
    for w in workouts:
        # Handle attribute differences (DB vs Dict vs Object)
        w_name = getattr(w, "name", None)
        w_type = getattr(w, "activity_type", getattr(w, "type", None))
        w_dist = getattr(w, "distance_m", 0.0)
        w_tod = getattr(w, "time_of_day", getattr(w, "timeOfDay", "AM"))
        w_date = getattr(w, "date", None)

        d_work = construct_domain_workout(w_name, w_type, w_dist, w_tod)

        # Find which day index
        if not w_date:
            continue

        # Ensure w_date is date object
        if hasattr(w_date, "date"):
            # If it's a datetime
            w_date = w_date.date()

        days_diff = (w_date - week_start).days
        day_keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if 0 <= days_diff < 7:
            days_map[day_keys[days_diff]].append(d_work)

    # Build Domain Days
    domain_days = {}
    day_keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, key in enumerate(day_keys):
        d_date = week_start + timedelta(days=i)
        domain_days[key] = DomainDay(date=d_date.isoformat(), workouts=days_map[key])

    return DomainWeek(
        weekStarting=week_start.isoformat(),
        status=status,
        days=domain_days,
    )


def prepare_validation_data(
    target_week_start: date,
    target_week_status: str,
    target_workouts: List[Any],
    focused_workout: Any,
    prev_week_start: date,
    prev_week_status: str,
    prev_week_workouts: List[Any],
) -> Tuple[DomainWeek, DomainWeek, DomainWorkout]:
    """
    Prepares the domain objects required for the ValidationEngine.
    """
    # 1. Create Domain Weeks
    domain_curr = create_domain_week(
        target_week_start, target_week_status, target_workouts
    )

    if prev_week_start and prev_week_workouts is not None:
        domain_prev = create_domain_week(
            prev_week_start, prev_week_status, prev_week_workouts
        )
    else:
        # Fallback for no previous week
        domain_prev = DomainWeek(weekStarting="1970-01-01", status="normal", days={})

    # 2. Construct Domain Workout for focus
    # Handle potentially mixed types for focused_workout
    f_name = getattr(focused_workout, "name", None)
    f_type = getattr(
        focused_workout, "activity_type", getattr(focused_workout, "type", None)
    )
    f_dist = getattr(focused_workout, "distance_m", 0.0)
    f_tod = getattr(
        focused_workout, "time_of_day", getattr(focused_workout, "timeOfDay", "AM")
    )

    domain_focused_workout = construct_domain_workout(f_name, f_type, f_dist, f_tod)

    return domain_prev, domain_curr, domain_focused_workout


def apply_workout_updates(workout: Any, update_data: Dict[str, Any]) -> None:
    """
    Mutates the 'workout' object with values from 'update_data'.
    """
    # Handle schema-specific mappings
    if "type" in update_data:
        # Map 'type' from schema to 'activity_type' in DB if exists
        val = update_data.pop("type")
        if hasattr(workout, "activity_type"):
            workout.activity_type = val
        elif hasattr(workout, "type"):
            workout.type = val

    if "timeOfDay" in update_data:
        # Map 'timeOfDay' from schema to 'time_of_day' in DB if exists
        val = update_data.pop("timeOfDay")
        if hasattr(workout, "time_of_day"):
            workout.time_of_day = val
        elif hasattr(workout, "timeOfDay"):
            workout.timeOfDay = val

    for key, value in update_data.items():
        if hasattr(workout, key):
            setattr(workout, key, value)


def sync_workout_name_to_distance(workout: Any) -> None:
    """
    Updates workout name string to match its distance if it follows standard patterns
    (e.g., "8k Run" -> "10k Run").
    """
    w_dist = getattr(workout, "distance_m", 0.0)
    w_name = getattr(workout, "name", "")

    km_val = w_dist / 1000
    # Match "8k Run", "10.5k Jog" etc.
    if re.match(r"^\d+(\.\d+)?k\s", w_name, re.IGNORECASE):
        parts = w_name.split(" ", 1)
        if len(parts) > 1:
            suffix = parts[1]
            if km_val.is_integer():
                new_name = f"{int(km_val)}k {suffix}"
            else:
                new_name = f"{km_val:g}k {suffix}"

            setattr(workout, "name", new_name)


def get_week_volume(week: Union[WeekSchema, DomainWeek]) -> float:
    """Calculates total distance for a WeekSchema or DomainWeek, strictly counting ONLY running activities."""
    total = 0.0
    # normalize types to lower case for comparison
    RUNNING_TYPES = [
        "run",
        "running",
        "trail",
        "trail_running",
        "long",
        "easy",
        "tempo",
        "intervals",
        "workout",
        "race",
        "fartlek",
        "hill",
        "hills",
        "threshold",
        "steady",
        "warmup",
        "cooldown",
    ]

    for day in week.days.values():
        for w in day.workouts:
            # Check against running types.
            # Note: w.type might be an Enum or string depending on where it came from (schema vs domain),
            # but in WeekSchema it is likely a string or ActivityType enum.
            w_type = str(w.type).lower()

            # Explicitly exclude non-running
            if w_type in [
                "cycling",
                "swimming",
                "bike",
                "swim",
                "pool",
                "cross",
                "strength",
                "yoga",
                "other",
            ]:
                continue

            # If it's a known running type OR just standard "Run"
            # Also catch generic cases where type might be "ActivityType.RUN" string representation
            if any(rt in w_type for rt in RUNNING_TYPES):
                total += w.distance_m

    return total


def scale_week_volume(week: WeekSchema, target_vol: float) -> None:
    """
    Scales the volume of workouts in a week to meet a target volume.
    Skips races and marathon-specific workouts.
    Mutates the WeekSchema object in place.
    """
    current = get_week_volume(week)
    if current == 0:
        return

    scale = target_vol / current

    for day in week.days.values():
        for w in day.workouts:
            if "marathon" in w.name.lower() or "42.2" in w.name:
                continue

            new_dist = w.distance_m * scale

            if "race" in w.type.lower():
                w.distance_m = new_dist
            else:
                # Round to nearest 1000m
                w.distance_m = round(new_dist / 1000) * 1000

            # Update Name using the helper logic
            # We use a temporary object wrapper or just implement logic here?
            # Ideally reuse the helper. Since 'w' in WeekSchema is pydantic/dataclass-like
            # let's apply the logic directly or ensure the helper handles it.
            # sync_workout_name_to_distance works on objects with attributes.
            sync_workout_name_to_distance(w)


def calculate_future_progression(
    weeks: List[WeekSchema], start_index: int, initial_baseline_vol: float
) -> None:
    """
    Iterates through weeks starting from start_index and applies progression logic.
    Mutates the list of weeks in place.
    """
    current_baseline_vol = initial_baseline_vol

    for i in range(start_index, len(weeks)):
        week = weeks[i]
        status = week.status.lower()

        has_race = False
        for d in week.days.values():
            for w in d.workouts:
                if "race" in w.type.lower():
                    has_race = True

        target_vol = 0

        if status == "normal" and not has_race:
            # Build phase: 7% increase
            build_factor = 1.07
            target_vol = current_baseline_vol * build_factor
            current_baseline_vol = target_vol  # Update baseline for next week
            scale_week_volume(week, target_vol)

        elif status in ["rest", "recovery"]:
            drop_factor = 0.65
            target_vol = current_baseline_vol * drop_factor
            # Do not update baseline
            scale_week_volume(week, target_vol)

        elif status == "taper":
            target_vol = current_baseline_vol * 0.60
            scale_week_volume(week, target_vol)

        elif status == "race" or has_race:
            # Cap if exceeds baseline?
            curr_vol = get_week_volume(week)
            if curr_vol > current_baseline_vol:
                scale_week_volume(week, current_baseline_vol)
            # Do not update baseline

        elif status == "marathon":
            pass
