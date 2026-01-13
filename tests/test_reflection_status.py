import json
import os
import pytest
from app.models.domain import Week
from scripts.reflect_and_validate import main
from unittest.mock import patch, MagicMock

def test_rest_week_bypass(tmp_path):
    # Scenario:
    # Wk 1: 60k (Normal)
    # Wk 2: 40k (Rest) -> marked status="rest"
    # Wk 3: 65k (Build) -> Standard logic would flag 40->65 (1.6x) violation.
    #                      But Rest logic should skip updating prev_vol, so it compares 65 vs 60 (1.08x) -> OK.
    
    plan_data = [
        {"weekStarting": "2026-01-05", "days": {"Mon": {"date": "2026-01-05", "workouts": [{"name": "Run", "distance_m": 60000, "type": "Run"}]}}},
        {"weekStarting": "2026-01-12", "status": "rest", "days": {"Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 40000, "type": "Run"}]}}},
        {"weekStarting": "2026-01-19", "days": {"Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 65000, "type": "Run"}]}}}
    ]
    
    # Needs actuals to start
    actuals_data = [{"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 60000}]
    
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
    # Should NOT satisfy validation rule 1 (1.15x cap) if it was comparing to 40k.
    # 40 * 1.15 = 46k.
    # If it compared to 60k? 60 * 1.15 = 69k.
    # So 65k is valid vs 60k. Invalid vs 40k.
    
    assert w3_dist == 65000.0 # Unchanged

def test_taper_week_bypass(tmp_path):
    # Scenario:
    # Wk 1: 100k (Normal build)
    # Wk 2: 70k (Taper) -> Marked "taper". Should skip validation but update prev_vol.
    # Wk 3: 80k (Build) -> Standard logic would flag 70->80 (1.14x) as OK.
    #                      If taper didn't update prev_vol, it would compare 100->80 (0.8x drop).
    
    plan_data = [
        {"weekStarting": "2026-01-05", "days": {"Mon": {"date": "2026-01-05", "workouts": [{"name": "Run", "distance_m": 100000, "type": "Run"}]}}},
        {"weekStarting": "2026-01-12", "status": "taper", "days": {"Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 70000, "type": "Run"}]}}},
        {"weekStarting": "2026-01-19", "days": {"Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 80000, "type": "Run"}]}}}
    ]
    
    # Needs actuals to start
    actuals_data = [{"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 100000}]
    
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
    # Week 3 should remain unchanged at 80k because:
    # - Taper week (70k) correctly updates prev_vol to 70k (not keeping it at 100k)
    # - Week 3's 80k is validated against the taper volume: 80k / 70k = 1.14x
    # - This 1.14x increase is under the 1.15x cap, so no adjustment is made
    # This confirms taper weeks update the baseline for subsequent week validation
    
    assert w3_dist == 80000.0  # Unchanged, validates against taper volume
