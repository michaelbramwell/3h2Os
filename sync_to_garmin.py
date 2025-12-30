import os
import re
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from garminconnect import Garmin

# Load credentials
load_dotenv()
email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")

if not email or not password or email == "your_email@example.com":
    print("Error: Please set GARMIN_EMAIL and GARMIN_PASSWORD in a .env file.")
    sys.exit(1)

def parse_distance(text):
    """Extracts distance in meters from strings like '8k Easy' or '6k Steady / 10k Int'."""
    matches = re.findall(r'(\d+)k', text)
    if not matches:
        return 0
    return sum(int(m) for m in matches) * 1000

def sync():
    # Initialize Garmin client
    client = Garmin(email, password)
    client.login()
    print(f"Logged in as {client.display_name}")

    # Read the plan
    with open("marathon_plan.md", "r") as f:
        content = f.read()

    # Extract target paces for descriptions
    paces_match = re.search(r'## Target Training Paces\n(.*?)\n\n', content, re.DOTALL)
    target_paces = paces_match.group(1).strip() if paces_match else ""

    # Find the table
    table_match = re.search(r'\| Week Starting \|.*?\|\n\| :--- \|.*?\|\n((?:\|.*?\|\n)+)', content, re.DOTALL)
    if not table_match:
        print("Error: Could not find the training plan table in marathon_plan.md")
        return

    rows = table_match.group(1).strip().split('\n')
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for row in rows:
        cols = [c.strip() for c in row.split('|')[1:-1]]
        if not cols:
            continue
        
        week_start_str = cols[0]
        # Handle date parsing (e.g., "Jan 5")
        try:
            # Assuming 2026 as per the context
            week_start = datetime.strptime(f"{week_start_str} 2026", "%b %d %Y")
        except ValueError:
            print(f"Skipping row with invalid date: {week_start_str}")
            continue

        print(f"\nProcessing week starting {week_start.date()}...")

        for i, day_text in enumerate(cols[1:8]): # Mon to Sun
            if day_text.lower() == "rest" or not day_text:
                continue
            
            current_date = week_start + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            
            distance_m = parse_distance(day_text)
            workout_name = f"{day_text}"
            
            print(f"  {date_str}: {workout_name} ({distance_m}m)")

            # Create a simple workout
            # Note: This is a simplified version. Garmin API is complex.
            # We'll use the 'upload_workout' method if we want structured steps,
            # but for now, let's try to schedule a simple activity or note.
            # Actually, the best way to 'sync' a plan is to create a Workout and then Schedule it.
            
            workout_payload = {
                "workoutName": workout_name,
                "description": f"Plan: {day_text}\n\nTarget Paces:\n{target_paces}",
                "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                "workoutSegments": [
                    {
                        "segmentOrder": 1,
                        "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                        "workoutSteps": [
                            {
                                "type": "ExecutableStepDTO",
                                "stepOrder": 1,
                                "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
                                "childStepId": None,
                                "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "distance"},
                                "endConditionValue": distance_m,
                                "targetType": {"targetTypeId": 1, "targetTypeKey": "no_target"}
                            }
                        ]
                    }
                ]
            }

            try:
                # 1. Upload the workout
                uploaded_workout = client.upload_workout(workout_payload)
                workout_id = uploaded_workout['workoutId']
                
                # 2. Schedule it
                client.schedule_workout(workout_id, date_str)
                print(f"    Successfully synced to {date_str}")
            except Exception as e:
                print(f"    Failed to sync {date_str}: {e}")

if __name__ == "__main__":
    sync()
