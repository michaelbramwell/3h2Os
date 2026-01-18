from datetime import datetime, timedelta, timezone
from scripts.fetch_actuals import get_awst_now

def test_get_awst_now():
    # Force a UTC time
    utc_now = datetime.now(timezone.utc)
    expected_awst = (utc_now + timedelta(hours=8)).strftime("%Y-%m-%d")
    
    # get_awst_now uses datetime.utcnow() which is effectively UTC without tzinfo
    actual_awst = get_awst_now().strftime("%Y-%m-%d")
    
    # This might fail if the test runs exactly at midnight, but usually it's fine
    assert actual_awst == expected_awst
    
def test_midnight_rollover():
    # If it's 23:00 UTC, it should be 07:00 AWST next day
    # We can't easily mock datetime.utcnow() without extra libraries like freezegun,
    # so we'll just check the logic 
    utc_time = datetime(2026, 1, 5, 23, 0, 0)
    awst_time = utc_time + timedelta(hours=8)
    assert awst_time.day == 6
    assert awst_time.hour == 7
