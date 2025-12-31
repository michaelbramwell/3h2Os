import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from garminconnect import Garmin

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class MarathonPlanSync:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv("GARMIN_EMAIL")
        self.password = os.getenv("GARMIN_PASSWORD")
        
        if not self.email or not self.password:
            logger.error("GARMIN_EMAIL or GARMIN_PASSWORD not set in .env")
            sys.exit(1)

        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            logger.info(f"Successfully logged in as {self.client.display_name}")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            sys.exit(1)

    def parse_plan(self, file_path: str) -> List[Dict[str, Any]]:
        """Reads the plan from plan.json."""
        with open(file_path, "r") as f:
            plan_data = json.load(f)

        entries = []
        for week in plan_data:
            for day_name, day_info in week["days"].items():
                for workout in day_info["workouts"]:
                    entries.append({
                        "date": day_info["date"],
                        "name": workout["name"],
                        "distance_m": workout["distance_m"]
                    })

        return entries

def get_pace_target(name: str) -> Optional[Dict[str, Any]]:
    """Returns pace target in m/s for different workout types."""
    if "MP" in name:
        return {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "targetValueOne": 1000 / (5.5 * 60),
            "targetValueTwo": 1000 / (5.66 * 60)
        }
    elif "Thresh" in name:
        return {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "targetValueOne": 1000 / (4.66 * 60),
            "targetValueTwo": 1000 / (4.83 * 60)
        }
    elif "Steady" in name:
        return {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "targetValueOne": 1000 / (5.16 * 60),
            "targetValueTwo": 1000 / (5.33 * 60)
        }
    elif "Easy" in name or "Recov" in name or "Trail" in name or "PLR" in name:
        return {
            "workoutTargetTypeId": 6,
            "workoutTargetTypeKey": "pace.zone",
            "targetValueOne": 1000 / (6.25 * 60), # 6:15
            "targetValueTwo": 1000 / (6.75 * 60)  # 6:45
        }
    
    return {
        "workoutTargetTypeId": 1,
        "workoutTargetTypeKey": "no.target"
    }

    def cleanup_existing_workouts(self, entries: List[Dict[str, Any]]):
        """Deletes existing workouts that match names in the plan to avoid duplicates."""
        logger.info("Checking for existing workouts to clean up...")
        plan_names = set(e["name"][:30] for e in entries)
        try:
            workouts = self.client.get_workouts()
            for w in workouts:
                if w['workoutName'] in plan_names:
                    # Use garth to delete since delete_workout is missing from high-level API
                    delete_url = f"/workout-service/workout/{w['workoutId']}"
                    self.client.garth.delete("connectapi", delete_url)
                    logger.info(f"Deleted existing workout: {w['workoutName']}")
        except Exception as e:
            logger.warning(f"Cleanup failed (non-critical): {e}")

    def sync(self):
        plan_path = os.path.join(os.getcwd(), "plan.json")
        entries = self.parse_plan(plan_path)

        if not entries:
            logger.warning("No entries found to sync.")
            return

        # Cleanup first
        self.cleanup_existing_workouts(entries)

        logger.info(f"Found {len(entries)} workouts to sync.")

        for entry in entries:
            try:
                target = get_pace_target(entry["name"])
                
                # Calculate estimated duration based on target pace or default 6:30 min/km
                if target.get("targetValueOne") and target.get("targetValueTwo"):
                    avg_speed = (target["targetValueOne"] + target["targetValueTwo"]) / 2
                else:
                    avg_speed = 1000 / (6.5 * 60) # 6:30 min/km default
                
                est_duration = int(entry["distance_m"] / avg_speed)

                workout_dict = {
                    "workoutName": entry["name"][:30],
                    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                    "estimatedDurationInSecs": est_duration,
                    "workoutSegments": [
                        {
                            "segmentOrder": 1,
                            "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                            "workoutSteps": [
                                {
                                    "type": "ExecutableStepDTO",
                                    "stepOrder": 1,
                                    "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
                                    "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "distance"},
                                    "endConditionValue": float(entry["distance_m"]),
                                    "targetType": target,
                                    "estimatedDurationInSecs": est_duration
                                }
                            ]
                        }
                    ]
                }

                uploaded = self.client.upload_workout(workout_dict)
                schedule_url = f"/workout-service/schedule/{uploaded['workoutId']}"
                self.client.garth.post("connectapi", schedule_url, json={"date": entry["date"]})
                
                logger.info(f"Synced: {entry['date']} - {entry['name']}")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to sync {entry['date']}: {e}")

if __name__ == "__main__":
    syncer = MarathonPlanSync()
    syncer.sync()
