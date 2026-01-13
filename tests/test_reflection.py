import json
import os
from scripts.reflect_and_validate import main, save_plan_to_db, load_plan
from unittest.mock import patch, MagicMock

def test_reflect_and_validate_scales_up_future(tmp_path):
    # Setup mock data
    # Week 1: Planned 40k. Actual 50k. (Ratio 1.25)
    # Week 2: Planned 44k. Expect Scalling to 44 * 1.25 = 55k.
    # Week 3: Planned 40k (Taper). Expect Scaling to 40 * 1.25 = 50k.
    
    plan_data = [
        {
            "weekStarting": "2026-01-05",
            "days": {
                "Mon": {"date": "2026-01-05", "workouts": [{"name": "10k Run", "distance_m": 40000, "type": "Run"}]}
            }
        },
        {
            "weekStarting": "2026-01-12",
            "days": {
                "Mon": {"date": "2026-01-12", "workouts": [{"name": "11k Run", "distance_m": 44000, "type": "Run"}]}
            }
        }
    ]
    
    actuals_data = [
        {"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 50000}
    ]
    
    os.chdir(tmp_path)
    # Write files
    # Note: main() looks for "data/plan.json" or "plan.json"; "data/actuals.json" or "actuals.json"
    
    with open("plan.json", "w") as f:
        json.dump(plan_data, f)
    with open("actuals.json", "w") as f:
        json.dump(actuals_data, f)
        
    # We need to mock save_plan_to_db to avoid DB interaction (or use in-mem DB logic if integrated)
    # Since main() calls save_plan(), which calls save_plan_to_db
    
    with patch("scripts.reflect_and_validate.save_plan_to_db") as mock_save:
        # Run main
        with patch("sys.stdout", new=MagicMock()): # Silence print
             main()
        
        # Check if plan.json on disk was updated
        with open("plan.json", "r") as f:
            new_plan = json.load(f)
            
        # Check Week 2 (Index 1)
        w2_wkt = new_plan[1]["days"]["Mon"]["workouts"][0]
        dist = w2_wkt["distance_m"]
        
        # Expected: 44000 * (50000/40000) = 55000
        # The validation logic (1.15 cap) might trigger?
        # Prev Vol (Week 1 Actual) = 50000.
        # Next Vol (Week 2 Planned Scaled) = 55000.
        # Ratio 55/50 = 1.1 <= 1.15. So it should hold.
        
        assert dist == 55000.0
        assert "55.0k" in w2_wkt["name"]

