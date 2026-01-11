import json
import pytest
from app.models.domain import load_plan, load_actuals, Week, ActualActivity

def test_load_plan(tmp_path):
    plan_file = tmp_path / "plan.json"
    plan_data = [
        {
            "weekStarting": "2026-01-05",
            "days": {
                "Mon": {
                    "date": "2026-01-05",
                    "workouts": [
                        {"name": "Rest", "type": "rest", "distance_m": 0, "timeOfDay": "AM"}
                    ]
                }
            }
        }
    ]
    plan_file.write_text(json.dumps(plan_data))
    
    loaded_plan = load_plan(str(plan_file))
    
    assert len(loaded_plan) == 1
    assert isinstance(loaded_plan[0], Week)
    assert loaded_plan[0].weekStarting == "2026-01-05"
    assert "Mon" in loaded_plan[0].days
    assert loaded_plan[0].days["Mon"].workouts[0].name == "Rest"

def test_load_actuals(tmp_path):
    actuals_file = tmp_path / "actuals.json"
    actuals_data = [
        {
            "date": "2026-01-06",
            "name": "Evening Run",
            "type": "running",
            "distance_m": 8000.0,
            "duration_s": 2400.0,
            "average_pace_m_s": 3.33,
            "hr_zones": [{"zoneNumber": 1, "secsInZone": 100}],
            "power_zones": []
        }
    ]
    actuals_file.write_text(json.dumps(actuals_data))
    
    loaded_actuals = load_actuals(str(actuals_file))
    
    assert len(loaded_actuals) == 1
    assert isinstance(loaded_actuals[0], ActualActivity)
    assert loaded_actuals[0].name == "Evening Run"
    assert loaded_actuals[0].distance_m == 8000.0

def test_load_plan_missing_file():
    plan = load_plan("non_existent.json")
    assert plan == []

def test_load_actuals_missing_file():
    actuals = load_actuals("non_existent.json")
    assert actuals == []
