import json
import os
from app.core.database import RunnerPlan, User
from scripts.reflect_and_validate import main
from unittest.mock import patch, MagicMock

def test_reflect_and_validate_scales_up_future_from_manual_edit(tmp_path):
    # Scenario:
    # DB has Week 2 (Next Week) at 50k. Week 3 at 55k.
    # User edits Disk Plan Week 2 to 60k.
    # Expectation: Week 3 scales to 66k (60/50 = 1.2x).
    
    # 1. Setup Data on Disk
    plan_data = [
        {
             # Week 1 (Actuals week - Ignored for this test logic, assumed match)
            "weekStarting": "2026-01-05", # Actuals exist for this
            "days": {}
        },
        {
            # Week 2 (Target of manual edit)
            "weekStarting": "2026-01-12",
            "days": {
                "Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 60000, "type": "Run"}]}
            }
        },
        {
            # Week 3 (To be scaled)
            "weekStarting": "2026-01-19",
            "days": {
                "Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 55000, "type": "Run"}]}
            }
        }
    ]
    
    actuals_data = [
         # Just some actuals so the script can establish "Previous"
        {"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 40000} 
    ]
    
    # 2. Setup DB Mock Data (The "Old" Plan)
    old_plan_data = [
        {"weekStarting": "2026-01-05", "days": {}},
        {
            "weekStarting": "2026-01-12",
             # Old Volume for W2 was 50k
            "days": {
                "Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 50000, "type": "Run"}]}
            }
        },
        {
             # Old Volume for W3 was 55k
            "weekStarting": "2026-01-19",
            "days": {
                "Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 55000, "type": "Run"}]}
            }
        }
    ]

    os.chdir(tmp_path)
    with open("plan.json", "w") as f:
        json.dump(plan_data, f)
    with open("actuals.json", "w") as f:
        json.dump(actuals_data, f)

    # Mock the DB Session interaction
    # The script calls: Session(engine) -> session.exec(...)
    
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    
    mock_plan = MagicMock(spec=RunnerPlan)
    mock_plan.plan_json = json.dumps(old_plan_data)
    
    # We need to mock Session(engine) to return a mock session that yields our mocks
    with patch("scripts.reflect_and_validate.Session") as MockSession:
        session_instance = MockSession.return_value.__enter__.return_value
        
        # Chains of exec().first()
        # 1. User query
        # 2. Plan query
        session_instance.exec.return_value.first.side_effect = [
            mock_user, # User found
            mock_plan, # Plan found
            mock_user # User found (inside save_plan_to_db maybe? or likely independent mock for save)
        ]

        # Ignore the save call
        with patch("scripts.reflect_and_validate.save_plan_to_db"):
            with patch("sys.stdout", new=MagicMock()):
                main()
    
    # Check results in file
    with open("plan.json", "r") as f:
        result = json.load(f)
        
    w3_dist = result[2]["days"]["Mon"]["workouts"][0]["distance_m"]
    
    # Expected: 55000 * (60000/50000) = 66000
    assert w3_dist == 66000.0
