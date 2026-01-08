import pytest
from fetch_actuals import GarminActualsFetcher
from models import ActualActivity

def test_enrich_zones_with_telemetry():
    # Mock thresholds from context.json
    pace_thresholds = [
        {"zone": 1, "lowBoundary_m_s": 0.5},
        {"zone": 2, "lowBoundary_m_s": 2.688},
        {"zone": 3, "lowBoundary_m_s": 3.115},
        {"zone": 4, "lowBoundary_m_s": 3.472},
        {"zone": 5, "lowBoundary_m_s": 3.717},
        {"zone": 6, "lowBoundary_m_s": 3.953}
    ]
    
    # Mock summaries
    hr_summary = [
        {"zoneNumber": 1, "zoneLowBoundary": 100},
        {"zoneNumber": 2, "zoneLowBoundary": 120},
        {"zoneNumber": 3, "zoneLowBoundary": 140},
        {"zoneNumber": 4, "zoneLowBoundary": 160},
        {"zoneNumber": 5, "zoneLowBoundary": 180}
    ]
    
    power_summary = [
        {"zoneNumber": 1, "zoneLowBoundary": 300},
        {"zoneNumber": 2, "zoneLowBoundary": 400}
    ]

    # Mock telemetry details
    mock_details = {
        "metricDescriptors": [
            {"key": "directSpeed", "metricsIndex": 0},
            {"key": "directHeartRate", "metricsIndex": 1},
            {"key": "directPower", "metricsIndex": 2},
            {"key": "sumElapsedDuration", "metricsIndex": 3}
        ],
        "activityDetailMetrics": [
            {"metrics": [3.0, 125, 350, 0.0]}, # Z2 pace, Z2 HR, Z1 Power
            {"metrics": [3.0, 125, 350, 10.0]}, # 10s passed
            {"metrics": [3.5, 165, 450, 20.0]}, # Z4 pace, Z4 HR, Z2 Power (10s passed)
        ]
    }

    fetcher = GarminActualsFetcher.__new__(GarminActualsFetcher)
    fetcher.client = type('MockClient', (), {'get_activity_details': lambda self, aid: mock_details})()

    hr_zones, power_zones, pace_zones = fetcher.enrich_zones_with_telemetry(
        123, 'running', pace_thresholds, hr_summary, power_summary
    )

    # Pace: 10s at 3.0 (Z2), 10s at 3.5 (Z4)
    z2_pace = next(z for z in pace_zones if z["zoneNumber"] == 2)
    z4_pace = next(z for z in pace_zones if z["zoneNumber"] == 4)
    assert z2_pace["secsInZone"] == 10.0
    assert abs(z2_pace["avgValue"] - 3.0) < 0.01
    assert z4_pace["secsInZone"] == 10.0
    assert abs(z4_pace["avgValue"] - 3.5) < 0.01

    # HR: 10s at 125 (Z2), 10s at 165 (Z4)
    z2_hr = next(z for z in hr_zones if z["zoneNumber"] == 2)
    z4_hr = next(z for z in hr_zones if z["zoneNumber"] == 4)
    assert z2_hr["secsInZone"] == 10.0
    assert z2_hr["avgValue"] == 125.0
    assert z4_hr["secsInZone"] == 10.0
    assert z4_hr["avgValue"] == 165.0

    # Power: 10s at 350 (Z1), 10s at 450 (Z2)
    z1_power = next(z for z in power_zones if z["zoneNumber"] == 1)
    z2_power = next(z for z in power_zones if z["zoneNumber"] == 2)
    assert z1_power["secsInZone"] == 10.0
    assert z1_power["avgValue"] == 350.0
    assert z2_power["secsInZone"] == 10.0
    assert z2_power["avgValue"] == 450.0

def test_enrich_zones_empty_telemetry():
    fetcher = GarminActualsFetcher.__new__(GarminActualsFetcher)
    fetcher.client = type('MockClient', (), {'get_activity_details': lambda self, aid: {}})()
    
    hr_orig = [{"zoneNumber": 1, "zoneLowBoundary": 100}]
    pw_orig = [{"zoneNumber": 1, "zoneLowBoundary": 300}]
    
    hr, pw, pace = fetcher.enrich_zones_with_telemetry(123, 'running', [], hr_orig, pw_orig)
    
    assert hr == hr_orig
    assert pw == pw_orig
    assert pace == []

def test_enrich_zones_skips_pace_for_cycling():
    pace_thresholds = [{"zone": 1, "lowBoundary_m_s": 2.22}]
    mock_details = {
        "metricDescriptors": [
            {"key": "directSpeed", "metricsIndex": 0},
            {"key": "sumElapsedDuration", "metricsIndex": 1}
        ],
        "activityDetailMetrics": [
            {"metrics": [10.0, 0.0]}, 
            {"metrics": [10.0, 10.0]},
        ]
    }
    fetcher = GarminActualsFetcher.__new__(GarminActualsFetcher)
    fetcher.client = type('MockClient', (), {'get_activity_details': lambda self, aid: mock_details})()
    
    _, _, pace_zones = fetcher.enrich_zones_with_telemetry(123, 'cycling', pace_thresholds, [], [])
    
    # Pace zones should be empty for cycling
    assert pace_zones[0]["secsInZone"] == 0.0
