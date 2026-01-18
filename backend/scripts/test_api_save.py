import httpx
import asyncio
from datetime import date

async def test_save():
    url = "http://localhost:8000/api/actuals"
    payload = [{
        "activityId": 123456789,
        "date": date.today().strftime("%Y-%m-%d"),
        "name": "Test Activity API Check",
        "type": "running",
        "distance_m": 5000,
        "duration_s": 1800,
        "average_pace_m_s": 2.7,
        "average_hr": 150,
        "max_hr": 170,
        "average_power": 250,
        "aerobic_te": 3.0,
        "anaerobic_te": 0.0,
        "training_load": 100,
        "calories": 500,
        "hr_zones": [],
        "pace_zones": [],
        "power_zones": []
    }]
    
    print(f"Sending payload to {url}...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_save())
