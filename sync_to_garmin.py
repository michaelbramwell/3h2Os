import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import List, Optional

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
        self.client: Optional[Garmin] = None

    def authenticate(self):
        """Authenticate with Garmin Connect."""
        if not self.email or not self.password or self.email == "your_email@example.com":
            logger.error("Missing credentials. Please check your .env file.")
            sys.exit(1)
        
        try:
            self.client = Garmin(self.email, self.password)
            self.client.login()
            logger.info(f"Successfully logged in as {self.client.display_name}")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            sys.exit(1)

    def parse_distance(self, text: str) -> int:
        """Extract total distance in meters from plan text."""
        matches = re.findall(r'(\d+)k', text)
        return sum(int(m) for m in matches) * 1000 if matches else 0

    def get_plan_data(self) -> List[dict]:
        """Parse marathon_plan.md and return structured data."""
        try:
            with open("marathon_plan.md", "r") as f:
                content = f.read()
        except FileNotFoundError:
            logger.error("marathon_plan.md not found.")
            return []

        # Extract target paces for descriptions
        paces_match = re.search(r'## Target Training Paces\n(.*?)\n\n', content, re.DOTALL)
        target_paces = paces_match.group(1).strip() if paces_match else ""

        # Find the table
        table_match = re.search(r'\| Week Starting \|.*?\|\n\| :--- \|.*?\|\n((?:\|.*?\|\n)+)', content, re.DOTALL)
        if not table_match:
            logger.error("Could not find training plan table.")
            return []

        rows = table_match.group(1).strip().split('\n')
        plan_entries = []

        for row in rows:
            cols = [c.strip() for c in row.split('|')[1:-1]]
            if not cols: continue
            
            try:
                week_start = datetime.strptime(f"{cols[0]} 2026", "%b %d %Y")
            except ValueError:
                continue

            for i, day_text in enumerate(cols[1:8]):
                if day_text.lower() == "rest" or not day_text:
                    continue
                
                plan_entries.append({
                    "date": (week_start + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "name": day_text,
                    "distance_m": self.parse_distance(day_text),
                    "description": f"Plan: {day_text}\n\nTarget Paces:\n{target_paces}"
                })
        
        return plan_entries

    def sync(self):
        """Main sync execution."""
        self.authenticate()
        entries = self.get_plan_data()
        
        if not entries:
            logger.warning("No entries found to sync.")
            return

        logger.info(f"Found {len(entries)} workouts to sync.")

        for entry in entries:
            try:
                workout_payload = {
                    "workoutName": entry["name"],
                    "description": entry["description"],
                    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                    "workoutSegments": [{
                        "segmentOrder": 1,
                        "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
                        "workoutSteps": [{
                            "type": "ExecutableStepDTO",
                            "stepOrder": 1,
                            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
                            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "distance"},
                            "endConditionValue": entry["distance_m"],
                            "targetType": {"targetTypeId": 1, "targetTypeKey": "no_target"}
                        }]
                    }]
                }

                uploaded = self.client.upload_workout(workout_payload)
                self.client.schedule_workout(uploaded['workoutId'], entry["date"])
                logger.info(f"Synced: {entry['date']} - {entry['name']}")
            except Exception as e:
                logger.error(f"Failed to sync {entry['date']}: {e}")

if __name__ == "__main__":
    syncer = MarathonPlanSync()
    syncer.sync()
