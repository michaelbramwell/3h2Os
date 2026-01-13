import json
import os
from app.core.database import RunnerPlan, User
from scripts.reflect_and_validate import main
from unittest.mock import patch, MagicMock

def test_reflect_and_validate_uses_history_if_active_matches(tmp_path):
    # Scenario:
    # 1. User sets Week 2 = 60k (Disk).
    # 2. User runs script. It saves 60k to Active DB. But didn't scale future (bug or crash).
    # 3. User realizes scaling failed. Runs script AGAIN.
    # 4. Script sees Active DB W2 = 60k. Disk = 60k. Ratio 1.0.
    # 5. Script should check Archived Plan. Archived W2 = 50k. Ratio 1.2.
    # 6. Script SCALES future.

    # Data Setup
    # Disk: W2 = 60k, W3 = 55k (Unscaled)
    # Active DB: W2 = 60k, W3 = 55k.
    # Archived DB: W2 = 50k, W3 = 55k.
    
    plan_data = [
        {"weekStarting": "2026-01-05", "days": {}},
        {"weekStarting": "2026-01-12", "days": {"Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 30000, "type": "Run"}]}}},
        {"weekStarting": "2026-01-19", "days": {"Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 25000, "type": "Run"}]}}}
    ]
    
    actuals_data = [{"date": "2026-01-05", "name": "Run", "type": "running", "distance_m": 20000}]
    
    active_plan_data = plan_data # Same as disk
    
    archived_plan_data = [
        {"weekStarting": "2026-01-05", "days": {}},
        {"weekStarting": "2026-01-12", "days": {"Mon": {"date": "2026-01-12", "workouts": [{"name": "Run", "distance_m": 25000, "type": "Run"}]}}},
        {"weekStarting": "2026-01-19", "days": {"Mon": {"date": "2026-01-19", "workouts": [{"name": "Run", "distance_m": 25000, "type": "Run"}]}}}
    ]
    
    os.chdir(tmp_path)
    with open("plan.json", "w") as f:
        json.dump(plan_data, f)
    with open("actuals.json", "w") as f:
        json.dump(actuals_data, f)
        
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    
    mock_active_plan = MagicMock(spec=RunnerPlan)
    mock_active_plan.plan_json = json.dumps(active_plan_data)
    mock_active_plan.id = 2
    
    mock_archived_plan = MagicMock(spec=RunnerPlan)
    mock_archived_plan.plan_json = json.dumps(archived_plan_data)
    mock_archived_plan.id = 1
    
    with patch("scripts.reflect_and_validate.Session") as MockSession:
        session_instance = MockSession.return_value.__enter__.return_value
        
        # 1. User
        # 2. Active Plan check
        # 3. Archived Plan check
        
        # Logic in script: 
        # user = session.exec(User).first()
        # active = session.exec(Active).first()
        # archived = session.exec(Archived).first()
        
        session_instance.exec.return_value.first.side_effect = [
            mock_user,
            mock_active_plan,
            mock_archived_plan,
            mock_user # Save logic
        ]
        
        with patch("scripts.reflect_and_validate.save_plan_to_db"):
            with patch("sys.stdout", new=MagicMock()):
                main()
                
    with open("plan.json", "r") as f:
        result = json.load(f)
        
    w3_dist = result[2]["days"]["Mon"]["workouts"][0]["distance_m"]
    # 25000 * 1.2 = 30000
    assert w3_dist == 30000.0

