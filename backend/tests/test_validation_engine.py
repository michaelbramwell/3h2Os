import pytest
from app.models.domain import Week, Day, Workout
from app.core.validation import ValidationEngine, ValidationIssue

@pytest.fixture
def empty_week():
    return Week(weekStarting="2026-01-01", days={})

@pytest.fixture
def normal_week():
    # 5 runs, total 50km
    # Long run 15km (30%)
    # Intensity 5km (10%)
    return Week(weekStarting="2026-01-08", days={
        "Mon": Day(date="2026-01-08", workouts=[Workout(name="Easy 8k", distance_m=8000, type="easy", timeOfDay="AM")]),
        "Tue": Day(date="2026-01-09", workouts=[Workout(name="Tempo 5k", distance_m=5000, type="tempo", timeOfDay="AM")]), # Intensity
        "Wed": Day(date="2026-01-10", workouts=[Workout(name="Easy 8k", distance_m=8000, type="easy", timeOfDay="AM")]),
        "Thu": Day(date="2026-01-11", workouts=[Workout(name="Rest", distance_m=0, type="rest", timeOfDay="AM")]),
        "Fri": Day(date="2026-01-12", workouts=[Workout(name="Easy 6k", distance_m=6000, type="easy", timeOfDay="AM")]),
        "Sat": Day(date="2026-01-13", workouts=[Workout(name="Long 15k", distance_m=15000, type="long", timeOfDay="AM")]), # Long
        "Sun": Day(date="2026-01-14", workouts=[Workout(name="Rest", distance_m=0, type="rest", timeOfDay="AM")]),
    })

@pytest.fixture
def heavy_week():
    # 70km total (40% jump from 50km) -> Should trigger Volume Spike
    return Week(weekStarting="2026-01-15", days={
        "Mon": Day(date="2026-01-15", workouts=[Workout(name="Easy 10k", distance_m=10000, type="easy", timeOfDay="AM")]),
        "Tue": Day(date="2026-01-16", workouts=[Workout(name="Tempo 8k", distance_m=8000, type="tempo", timeOfDay="AM")]),
        "Wed": Day(date="2026-01-17", workouts=[Workout(name="Easy 10k", distance_m=10000, type="easy", timeOfDay="AM")]),
        "Thu": Day(date="2026-01-18", workouts=[Workout(name="Easy 5k", distance_m=5000, type="easy", timeOfDay="AM")]),
        "Fri": Day(date="2026-01-19", workouts=[Workout(name="Easy 7k", distance_m=7000, type="easy", timeOfDay="AM")]),
        # Long Run 30km (42% of 70km) -> Should trigger Long Run Ratio
        "Sat": Day(date="2026-01-20", workouts=[Workout(name="Long 30k", distance_m=30000, type="long", timeOfDay="AM")]),
        "Sun": Day(date="2026-01-21", workouts=[Workout(name="Rest", distance_m=0, type="rest", timeOfDay="AM")]),
    })

def test_volume_calculation(normal_week):
    engine = ValidationEngine()
    vol = engine._calculate_volume(normal_week)
    # 8+5+8+0+6+15+0 = 42km ... wait
    # 8000+5000+8000+0+6000+15000 = 42000
    assert vol == 42000

def test_intensity_calculation(normal_week):
    engine = ValidationEngine()
    # Only "Tempo 5k" is intensity
    int_vol = engine._calculate_intensity_volume(normal_week)
    assert int_vol == 5000

def test_validate_progression_spike(normal_week, heavy_week):
    engine = ValidationEngine(max_volume_increase_ratio=1.15) # 15% max
    
    # 42k -> 70k is a huge jump
    issues = engine.validate_progression(normal_week, heavy_week)
    
    volume_errors = [i for i in issues if i.rule_id == "volume_progression"]
    assert len(volume_errors) == 1
    assert volume_errors[0].severity == "error"
    assert "Volume spike detected" in volume_errors[0].message

def test_validate_long_run_ratio(heavy_week):
    engine = ValidationEngine(max_long_run_ratio=0.40)
    
    # Total 70k. Long Run 30k. Ratio = 0.428 (42.8%)
    issues = engine.validate_structure(heavy_week)
    
    lr_errors = [i for i in issues if i.rule_id == "long_run_ratio"]
    assert len(lr_errors) > 0
    # Should be error or warning depending on logic. Logic says error if vol > 30k
    assert lr_errors[0].severity == "error"

def test_validate_80_20_rule():
    # Construct a week with too much intensity
    week = Week(weekStarting="2026-01-01", days={
        "Mon": Day(date="2026-01-01", workouts=[Workout(name="Hard 10k", distance_m=10000, type="intervals", timeOfDay="AM")]),
        "Tue": Day(date="2026-01-02", workouts=[Workout(name="Easy 5k", distance_m=5000, type="easy", timeOfDay="AM")]),
    }) # Total 15k, Intensity 10k (66%)
    
    engine = ValidationEngine(max_intensity_ratio=0.25)
    issues = engine.validate_structure(week)
    
    int_errors = [i for i in issues if i.rule_id == "intensity_ratio"]
    assert len(int_errors) == 1
    assert "High Intensity" in int_errors[0].message
