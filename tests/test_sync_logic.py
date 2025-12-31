import pytest
from sync_to_garmin import get_pace_target

def test_get_pace_target_mp():
    target = get_pace_target("10k MP Run")
    assert target["workoutTargetTypeKey"] == "pace.zone"
    # 5:30 min/km = 1000 / (5.5 * 60) = 3.03 m/s
    assert round(target["targetValueOne"], 2) == 3.03

def test_get_pace_target_thresh():
    target = get_pace_target("5k Thresh")
    assert target["workoutTargetTypeKey"] == "pace.zone"
    # 4:40 min/km = 1000 / (4.66 * 60) = 3.57 m/s
    assert round(target["targetValueOne"], 2) == 3.58

def test_get_pace_target_steady():
    target = get_pace_target("8k Steady")
    assert target["workoutTargetTypeKey"] == "pace.zone"
    # 5:10 min/km = 1000 / (5.16 * 60) = 3.22 m/s
    assert round(target["targetValueOne"], 2) == 3.23

def test_get_pace_target_easy():
    target = get_pace_target("12k Easy")
    assert target["workoutTargetTypeKey"] == "pace.zone"
    # 6:15 min/km = 1000 / (6.25 * 60) = 2.66 m/s
    assert round(target["targetValueOne"], 2) == 2.67

def test_get_pace_target_no_target():
    target = get_pace_target("Rest Day")
    assert target["workoutTargetTypeKey"] == "no.target"
