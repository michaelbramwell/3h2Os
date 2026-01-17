import json
from scripts.reflect_and_validate import main
from unittest.mock import patch, MagicMock

def test_baseline_lookback_after_rest_week(tmp_path):
    # Scenario:
    # Wk 1: 60k Actual (Normal)
    # Wk 2: 40k Actual (Rest)
    # Wk 3: 65k Plan (Normal)
    
    # Ideally, the validator should look back past Wk 2 to Wk 1 to find the 60k baseline.
    # So 40k -> 65k is allowed because valid comparison is 60k -> 65k.
    
    plan_data = [
        {
            "weekStarting": "2026-01-05", 
            "status": "normal",
            "days": {"Mon": {"date": "2026-01-05", "workouts": [{"name": "Run", "distance_m": 60000, "type": "Run"}]}}
        },
        {
            "weekStarting": "2026-01-12", 
            "status": "rest", 
            "days": {"Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 40000, "type": "Run"}]}}
        },
        {
            "weekStarting": "2026-01-19", 
            "status": "normal",
            "days": {"Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 65000, "type": "Run"}]}}
        }
    ]
    
    actuals_data = [
        {"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 60000},
        {"date": "2026-01-12", "name": "Run", "type": "running", "distance_m": 40000},
    ]
    
    import os
    os.chdir(tmp_path)
    with open("plan.json", "w") as f:
        json.dump(plan_data, f)
    with open("actuals.json", "w") as f:
        json.dump(actuals_data, f)
        
    # Mock DB interactions
    with patch("scripts.reflect_and_validate.Session"):
        with patch("scripts.reflect_and_validate.save_plan_to_db"):
            with patch("sys.stdout", new=MagicMock()): # Suppress output
                main()
                
    with open("plan.json", "r") as f:
        result = json.load(f)
        
    w3_dist = result[2]["days"]["Mon"]["workouts"][0]["distance_m"]
    
    # If logic works, it keeps 65k. 
    # If logic fails (uses 40k baseline), it caps at 40k * 1.15 = 46k.
    assert w3_dist == 65000.0, f"Week 3 distance scaled down to {w3_dist}, expected 65000.0"

def test_baseline_lookback_after_race_week(tmp_path):
    # Scenario:
    # Wk 1: 60k Actual (Normal)
    # Wk 2: 50k Actual (Race Week - typically lower volume)
    # Wk 3: 65k Plan (Normal)
    
    plan_data = [
        {
            "weekStarting": "2026-01-05", "status": "normal",
            "days": {"Mon": {"date": "2026-01-05", "workouts": [{"name": "Run", "distance_m": 60000, "type": "Run"}]}}
        },
        {
            "weekStarting": "2026-01-12", "status": "race",
            "days": {
                "Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 10000, "type": "Run"}]},
                "Sun": {"date": "2026-01-18", "workouts": [{"name": "Race", "distance_m": 40000, "type": "Race"}]}
            }
        },
        {
            "weekStarting": "2026-01-19", "status": "normal",
            "days": {"Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 65000, "type": "Run"}]}}
        }
    ]
    
    # Actuals mirror plan
    actuals_data = [
        {"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 60000},
        {"date": "2026-01-12", "name": "Run", "type": "running", "distance_m": 10000},
        {"date": "2026-01-18", "name": "Race", "type": "running", "distance_m": 40000}, # Total 50k
    ]
    
    import os
    os.chdir(tmp_path)
    with open("plan.json", "w") as f:
        json.dump(plan_data, f)
    with open("actuals.json", "w") as f:
        json.dump(actuals_data, f)
        
    with patch("scripts.reflect_and_validate.Session"):
        with patch("scripts.reflect_and_validate.save_plan_to_db"):
            with patch("sys.stdout", new=MagicMock()):
                main()
                
    with open("plan.json", "r") as f:
        result = json.load(f)
        
    w3_dist = result[2]["days"]["Mon"]["workouts"][0]["distance_m"]
    # 50k * 1.15 = 57.5k. 
    # 60k * 1.15 = 69k.
    # 65k should be valid if looking back to 60k.
    assert w3_dist == 65000.0, f"Week 3 distance scaled down to {w3_dist}, expected 65000.0"
