import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

from dotenv import load_dotenv
from garminconnect import Garmin

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class GarminActualsFetcher:
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

    def filter_activities(self, activities: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Filters raw Garmin activities by date range and maps to our schema."""
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        filtered_activities = []
        for act in activities:
            # act['startTimeLocal'] is usually "2025-12-31 08:00:00"
            act_dt = datetime.strptime(act['startTimeLocal'], "%Y-%m-%d %H:%M:%S")
            
            if start_dt <= act_dt <= end_dt:
                filtered_activities.append({
                    "date": act_dt.strftime("%Y-%m-%d"),
                    "name": act['activityName'],
                    "type": act['activityType']['typeKey'],
                    "distance_m": act['distance'],
                    "duration_s": act['duration'],
                    "average_pace_m_s": act.get('averageSpeed'), # m/s
                    "average_hr": act.get('averageHR'),
                    "calories": act.get('calories'),
                    "activityId": act['activityId']
                })
        return filtered_activities

    def fetch_activities(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Fetches activities between start_date and end_date (YYYY-MM-DD)."""
        logger.info(f"Fetching activities from {start_date} to {end_date}...")
        
        # Garmin API uses start and limit, so we fetch a batch and filter
        # For a 14-week plan, 100 activities should be plenty
        activities = self.client.get_activities(0, 100)
        
        filtered_activities = self.filter_activities(activities, start_date, end_date)
        
        logger.info(f"Found {len(filtered_activities)} activities in range.")
        return filtered_activities

    def save_actuals(self, activities: List[Dict[str, Any]], file_path: str = "actuals.json"):
        """Saves the activities to a JSON file."""
        with open(file_path, "w") as f:
            json.dump(activities, f, indent=2)
        logger.info(f"Saved actuals to {file_path}")
        
        # Update context.json status
        try:
            with open("context.json", "r") as f:
                context = json.load(f)
            
            context["status"]["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")
            context["status"]["garminSync"] = f"Plan synced. {len(activities)} actuals recorded."
            
            with open("context.json", "w") as f:
                json.dump(context, f, indent=2)
            logger.info("Updated context.json status.")
        except Exception as e:
            logger.error(f"Failed to update context.json: {e}")

def main():
    fetcher = GarminActualsFetcher()
    
    # Plan starts Jan 5, 2026. We'll fetch from then until today.
    # Since today is Dec 31, 2025, we'll fetch a small range for testing if needed,
    # but the logic should target the plan dates.
    start_date = "2026-01-05"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    # If today is before the plan start, let's just fetch the last 7 days for testing
    if end_date < start_date:
        logger.info("Today is before plan start. Fetching last 7 days for testing purposes.")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    activities = fetcher.fetch_activities(start_date, end_date)
    fetcher.save_actuals(activities)

if __name__ == "__main__":
    main()
