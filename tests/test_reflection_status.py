import json
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
    # Should NOT satisfy validation rule 1 (1.15x cap) if it was comparing to 40k.
    # 40 * 1.15 = 46k.
    # If it compared to 60k? 60 * 1.15 = 69k.
    # So 65k is valid vs 60k. Invalid vs 40k.
    
    assert w3_dist == 65000.0 # Unchanged

def test_taper_week_bypass(tmp_path):
    # Scenario:
    # Wk 1: 100k
    # Wk 2: 70k (Taper) -> Marked "taper".
    # Wk 3: 40k (Race) -> Marked "race" implicitly via workout.
    
    # We just want to ensure Taper doesn't trigger "High to Low" warnings (though we don't have minimum caps yet)
    # But mainly that Taper *updates* the prev_vol so that subsequent weeks (if any) are based on the taper?
    # Actually, usually Taper leads to Race which leads to Recovery.
    pass
