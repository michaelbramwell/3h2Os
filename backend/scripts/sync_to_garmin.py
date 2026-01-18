import json
import logging
import os
import re
import sys
import time
import base64
import zipfile
import io
import shutil
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv
from garminconnect import Garmin
from sqlmodel import Session

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.core.database import engine
from app.services.plans import PlanService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

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

class MarathonPlanSync:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv("GARMIN_EMAIL")
        self.password = os.getenv("GARMIN_PASSWORD")
        self.tokens_b64 = os.getenv("GARMIN_TOKENS")
        if self.tokens_b64:
            self.tokens_b64 = self.tokens_b64.strip()

        # Try to restore tokens first
        if self.tokens_b64:
            try:
                token_dir = os.path.expanduser("~/.garth")
                if not os.path.exists(token_dir):
                    os.makedirs(token_dir)
                
                # Decode and extract
                zip_data = base64.b64decode(self.tokens_b64)
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    zf.extractall(token_dir)
                logger.info("Restored Garmin tokens from environment variable.")
            except Exception as e:
                logger.warning(f"Failed to restore tokens: {e}")

        self.client = None
        
        # 1. Try token login
        try:
            logger.info("Attempting login with stored tokens...")
            self.client = Garmin()
            self.client.login(os.path.expanduser("~/.garth"))
            logger.info(f"Successfully logged in with tokens as {self.client.display_name}")
        except Exception as e_token:
            logger.warning(f"Token login failed: {e_token}")
            self.client = None

        # 2. Fallback to password login
        if not self.client:
            if not self.email or not self.password:
                logger.error("Login failed and GARMIN_EMAIL/GARMIN_PASSWORD not set.")
                sys.exit(1)
                
            try:
                logger.info("Attempting login with credentials...")
                self.client = Garmin(self.email, self.password)
                self.client.login()
                logger.info(f"Successfully logged in with credentials as {self.client.display_name}")
            except Exception as e:
                logger.error(f"Login failed: {e}")
                sys.exit(1)

    def parse_plan(self) -> List[Dict[str, Any]]:
        """Reads the plan from Database."""
        entries = []
        with Session(engine) as session:
             service = PlanService(session)
             try:
                 plan_weeks = service.get_active_plan()
             except Exception:
                 logging.error("No active plan found in DB.")
                 return []
        
        for week in plan_weeks:
            for day_name, day_info in week.days.items():
                for workout in day_info.workouts:
                    entries.append({
                        "date": day_info.date,
                        "name": workout.name,
                        "distance_m": workout.distance_m
                    })
        return entries



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
        # Read from DB
        entries = self.parse_plan()

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
    try:
        syncer = MarathonPlanSync()
        syncer.sync()
    except Exception:
        import traceback
        traceback.print_exc()
