import pytest
from app.models.domain import Week, Day, Workout
from app.core.validation import ValidationEngine


from app.core.plan_logic import get_week_volume


def test_cycling_does_not_inflate_running_volume():
    """
    Reproduction test for the '91km warning' bug.
    Ensures that adding a large cycling volume does not increase the calculate_volume()
    result, which is used for weekly progression validation.
    """

    # Week with 10k Run + 50k Cycle
    mixed_week = Week(
        weekStarting="2026-01-08",
        days={
            "Mon": Day(
                date="2026-01-08",
                workouts=[
                    Workout(
                        name="Easy 10k", distance_m=10000, type="Run", timeOfDay="AM"
                    )
                ],
            ),
            "Tue": Day(
                date="2026-01-09",
                workouts=[
                    Workout(
                        name="Bike Ride",
                        distance_m=50000,
                        type="Cycling",
                        timeOfDay="AM",
                    )
                ],
            ),
            "Wed": Day(
                date="2026-01-10",
                workouts=[
                    Workout(
                        name="Swim", distance_m=2000, type="Swimming", timeOfDay="AM"
                    )
                ],
            ),
            # Another run to make sure running sums correctly
            "Thu": Day(
                date="2026-01-11",
                workouts=[
                    Workout(
                        name="Easy 5k", distance_m=5000, type="Easy Run", timeOfDay="AM"
                    )
                ],
            ),
        },
    )

    # Calculate volume
    vol = get_week_volume(mixed_week)

    # Expected: 10,000 (Run) + 5,000 (Easy Run) + 2,000 (Swim) = 17,000m
    # The 50,000m Bike should be ignored.
    # Note: We now count Swimming in volume as it's a primary supported sport,
    # whereas Cycling is treated as cross-training.
    assert vol == 17000, f"Volume should be 17000 (15km Run + 2km Swim), but got {vol}"


def test_validate_progression_ignores_cross_training():
    """
    Ensures that a week with massive cross-training doesn't trigger a
    'volume progression' error against a normal running week.
    """
    prev_week = Week(
        weekStarting="2026-01-01",
        days={
            "Mon": Day(
                date="2026-01-01",
                workouts=[
                    Workout(
                        name="Easy 10k", distance_m=10000, type="Run", timeOfDay="AM"
                    )
                ],
            )
        },
    )  # 10km prev volume

    # Current week: 12km Running (20% increase, safe) + 100km Cycling
    curr_week = Week(
        weekStarting="2026-01-08",
        days={
            "Mon": Day(
                date="2026-01-08",
                workouts=[
                    Workout(
                        name="Easy 12k", distance_m=12000, type="Run", timeOfDay="AM"
                    )
                ],
            ),
            "Tue": Day(
                date="2026-01-09",
                workouts=[
                    Workout(
                        name="Long Ride",
                        distance_m=100000,
                        type="Cycling",
                        timeOfDay="AM",
                    )
                ],
            ),
        },
    )

    engine = ValidationEngine(max_volume_increase_ratio=1.15)

    # If cycling counted, this would be 112km vs 10km (1000% increase) -> ERROR
    # If cycling ignored, this is 12km vs 10km (20% increase) -> PASS (or minor warning depending on threshold logic)

    issues = engine.validate_progression(prev_week, curr_week)

    # Filter for volume progression errors
    vol_errors = [i for i in issues if i.rule_id == "volume_progression"]

    # 12k vs 10k is a 20% increase.
    # Logic: if diff > 5k (no, 2k diff).
    # Check logic: if diff > 5000: ...
    # Here diff is 2000, so it should be IGNORED completely by the 'small volume buffer' rule.
    # Therefore, 0 errors expected.

    assert len(vol_errors) == 0, (
        f"Should not flag volume increase, but got: {vol_errors}"
    )
