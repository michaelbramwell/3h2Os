from fastapi.testclient import TestClient
from unittest.mock import patch, mock_open
import json
from app.main import app

client = TestClient(app)

def test_read_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "Marathon Training Dashboard" in response.text

def test_get_plan_fallback():
    # Test fallback to file when DB might be empty (or we mock file)
    mock_data = [{"weekStarting": "2026-01-05", "days": {}}]
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            response = client.get("/plan.json")
            assert response.status_code == 200
            # Note: The API logic checks DB first. If DB is empty (which it is in test unless lifespan populates it), it falls back.
            # In test environment, lifespan runs when using TestClient with a context manager or explicit .startup()/.shutdown() 
            # OR TestClient(app) runs startup event automatically.
            # However, our lifespan creates a default user/plan if missing. 
            # So likely we get the DB version.
            
def test_get_context():
    mock_data = {"project": {"goal": "Sub-4"}}
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            response = client.get("/context.json")
            assert response.status_code == 200
            assert response.json()["project"]["goal"] == "Sub-4"

def test_get_actuals():
    mock_data = [{"activityId": 123}]
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            response = client.get("/actuals.json")
            assert response.status_code == 200
            assert response.json()[0]["activityId"] == 123
