import pytest
from fetch_actuals import GarminActualsFetcher

def test_filter_activities():
    # Mock data
    raw_activities = [
        {
            "startTimeLocal": "2026-01-06 08:00:00",
            "activityName": "Morning Run",
            "activityType": {"typeKey": "running"},
            "distance": 5000,
            "duration": 1500,
            "averageSpeed": 3.33,
            "averageHR": 150,
            "calories": 400,
            "activityId": 12345
        },
        {
            "startTimeLocal": "2026-01-04 08:00:00", # Before range
            "activityName": "Pre-plan Run",
            "activityType": {"typeKey": "running"},
            "distance": 3000,
            "duration": 900,
            "averageSpeed": 3.33,
            "averageHR": 140,
            "calories": 250,
            "activityId": 12344
        }
    ]
    
    # We need to bypass __init__ because it tries to login
    fetcher = GarminActualsFetcher.__new__(GarminActualsFetcher)
    
    filtered = fetcher.filter_activities(raw_activities, "2026-01-05", "2026-01-10")
    
    assert len(filtered) == 1
    assert filtered[0].name == "Morning Run"
    assert filtered[0].date == "2026-01-06"
    assert filtered[0].distance_m == 5000
