import json
import os
import pytest
from generate_plan_md import generate_marathon_plan, generate_context_md

def test_generate_marathon_plan(tmp_path):
    # Create a mock plan.json
    plan_data = [
        {
            "weekStarting": "2026-01-05",
            "days": {
                "Mon": {"date": "2026-01-05", "workouts": []},
                "Tue": {"date": "2026-01-06", "workouts": [{"name": "5k Easy", "distance_m": 5000, "type": "Easy"}]},
                "Wed": {"date": "2026-01-07", "workouts": []},
                "Thu": {"date": "2026-01-08", "workouts": []},
                "Fri": {"date": "2026-01-09", "workouts": []},
                "Sat": {"date": "2026-01-10", "workouts": []},
                "Sun": {"date": "2026-01-11", "workouts": []}
            }
        }
    ]
    
    # Change directory to tmp_path to avoid messing with real files
    os.chdir(tmp_path)
    
    with open("plan.json", "w") as f:
        json.dump(plan_data, f)
        
    generate_marathon_plan()
    
    assert os.path.exists("marathon_plan.md")
    with open("marathon_plan.md", "r") as f:
        content = f.read()
        assert "# Marathon Plan" in content
        assert "Jan 5" in content
        assert "5k Easy" in content

def test_generate_context_md(tmp_path):
    # Create a mock context.json
    context_data = {
        "project": {
            "event": "Test Marathon",
            "eventDate": "2026-04-12",
            "goal": "Sub-4",
            "rules": ["No emojis"]
        },
        "runner": {
            "age": 48,
            "gender": "Male",
            "height_cm": 185,
            "weight_kg": {"current": 97, "target": 90},
            "personalBests": {"5km": "22:06"}
        },
        "planOverview": {
            "durationWeeks": 14,
            "peakVolume_km": 111,
            "frequencyDaysPerWeek": 6,
            "strategy": "Test strategy"
        },
        "milestones": [],
        "philosophy": {
            "crampPrevention": {"mechanical": "M", "metabolic": "L", "fueling": "F"},
            "weeklyStructure": {"Wednesday": "W", "Thursday": "T", "Sunday": "S"}
        },
        "status": {
            "lastUpdated": "2025-12-31",
            "phase": "Test",
            "architecture": "A",
            "garminSync": "G",
            "tooling": "T",
            "nextAction": "N"
        }
    }
    
    os.chdir(tmp_path)
    
    with open("context.json", "w") as f:
        json.dump(context_data, f)
        
    generate_context_md()
    
    assert os.path.exists("context.md")
    with open("context.md", "r") as f:
        content = f.read()
        assert "# Training Context: Test Marathon" in content
        assert "Test strategy" in content
