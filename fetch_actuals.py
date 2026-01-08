import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from dotenv import load_dotenv
from garminconnect import Garmin
from models import ActualActivity

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

    def filter_activities(self, activities: List[Dict[str, Any]], start_date: str, end_date: str) -> List[ActualActivity]:
        """Filters raw Garmin activities by date range and maps to our schema."""
        filtered_activities: List[ActualActivity] = []
        
        # Load pace thresholds from context.json
        pace_thresholds = []
        try:
            with open("context.json", "r") as f:
                context = json.load(f)
                pace_thresholds = context.get("runner", {}).get("trainingZones", {}).get("pace", [])
        except Exception as e:
            logger.warning(f"Could not load pace thresholds from context.json: {e}")

        for act in activities:
            # act['startTimeLocal'] is usually "2025-12-31 08:00:00"
            act_date_str = act['startTimeLocal'].split(' ')[0]
            
            if start_date <= act_date_str <= end_date:
                activity_id = act['activityId']
                hr_zones = []
                power_zones = []
                pace_zones = []

                # Fetch detailed zones for running/cycling
                if act['activityType']['typeKey'] in ['running', 'cycling']:
                    # Try to get existing summaries to use as boundaries
                    raw_hr_summary = []
                    raw_power_summary = []
                    try:
                        raw_hr_summary = self.client.get_activity_hr_in_timezones(activity_id)
                    except Exception: pass
                    
                    try:
                        raw_power_summary = self.client.connectapi(f"activity-service/activity/{activity_id}/powerTimeInZones")
                    except Exception: pass

                    # Enrich zones with averages from telemetry
                    try:
                        hr_zones, power_zones, pace_zones = self.enrich_zones_with_telemetry(
                            activity_id, 
                            act['activityType']['typeKey'],
                            pace_thresholds,
                            raw_hr_summary,
                            raw_power_summary
                        )
                    except Exception as e:
                        logger.warning(f"Failed to enrich zones for {activity_id}: {e}")
                        # Fallback to summaries if telemetry fails
                        hr_zones = raw_hr_summary
                        power_zones = raw_power_summary

                filtered_activities.append(ActualActivity(
                    date=act_date_str,
                    name=act['activityName'],
                    type=act['activityType']['typeKey'],
                    distance_m=act['distance'],
                    duration_s=act['duration'],
                    average_pace_m_s=act.get('averageSpeed'),
                    average_hr=act.get('averageHR'),
                    max_hr=act.get('maxHR'),
                    average_power=act.get('avgPower'),
                    aerobic_te=act.get('aerobicTrainingEffect'),
                    anaerobic_te=act.get('anaerobicTrainingEffect'),
                    training_load=act.get('activityTrainingLoad'),
                    calories=act.get('calories'),
                    activityId=activity_id,
                    hr_zones=hr_zones,
                    power_zones=power_zones,
                    pace_zones=pace_zones
                ))
        return filtered_activities

    def enrich_zones_with_telemetry(self, activity_id: int, act_type: str, pace_thresholds: List[Dict], hr_summary: List[Dict], power_summary: List[Dict]):
        """Derives time and average values for Pace, HR, and Power zones from raw telemetry."""
        logger.info(f"Enriching zone data with telemetry for activity {activity_id}...")
        details = self.client.get_activity_details(activity_id)
        
        metrics = details.get("activityDetailMetrics", [])
        descriptors = details.get("metricDescriptors", [])
        
        if not metrics or not descriptors:
            return hr_summary, power_summary, []
            
        # Map descriptor keys to indices
        idx_map = {d["key"]: d["metricsIndex"] for d in descriptors}
        
        speed_idx = idx_map.get("directSpeed")
        hr_idx = idx_map.get("directHeartRate")
        power_idx = idx_map.get("directPower")
        elapsed_idx = idx_map.get("sumElapsedDuration")
        
        if elapsed_idx is None:
            return hr_summary, power_summary, []

        # Setup accumulator structures
        def init_acc(thresholds, key_name):
            return {t[key_name]: {"secs": 0.0, "sum": 0.0, "boundary": t["lowBoundary"]} for t in thresholds}

        # Format summaries/thresholds for processing
        pace_proc = [{"zone": t["zone"], "lowBoundary": t["lowBoundary_m_s"]} for t in pace_thresholds]
        hr_proc = [{"zone": t["zoneNumber"], "lowBoundary": t["zoneLowBoundary"]} for t in hr_summary]
        power_proc = [{"zone": t["zoneNumber"], "lowBoundary": t["zoneLowBoundary"]} for t in power_summary]

        pace_acc = init_acc(pace_proc, "zone")
        hr_acc = init_acc(hr_proc, "zone")
        power_acc = init_acc(power_proc, "zone")

        prev_elapsed = 0.0
        for m in metrics:
            sm = m.get("metrics", [])
            curr_elapsed = sm[elapsed_idx] if len(sm) > elapsed_idx else None
            if curr_elapsed is None: continue
            
            duration = curr_elapsed - prev_elapsed
            if duration <= 0:
                prev_elapsed = curr_elapsed
                continue

            # Process Pace (ONLY for running)
            if act_type == 'running' and speed_idx is not None and len(sm) > speed_idx and sm[speed_idx] is not None:
                val = sm[speed_idx]
                zone = 0
                for t in sorted(pace_proc, key=lambda x: x["lowBoundary"], reverse=True):
                    if val >= t["lowBoundary"]:
                        zone = t["zone"]
                        break
                if zone > 0:
                    pace_acc[zone]["secs"] += duration
                    pace_acc[zone]["sum"] += val * duration

            # Process HR
            if hr_idx is not None and len(sm) > hr_idx and sm[hr_idx] is not None:
                val = sm[hr_idx]
                zone = 0
                for t in sorted(hr_proc, key=lambda x: x["lowBoundary"], reverse=True):
                    if val >= t["lowBoundary"]:
                        zone = t["zone"]
                        break
                if zone > 0:
                    hr_acc[zone]["secs"] += duration
                    hr_acc[zone]["sum"] += val * duration

            # Process Power
            if power_idx is not None and len(sm) > power_idx and sm[power_idx] is not None:
                val = sm[power_idx]
                zone = 0
                for t in sorted(power_proc, key=lambda x: x["lowBoundary"], reverse=True):
                    if val >= t["lowBoundary"]:
                        zone = t["zone"]
                        break
                if zone > 0:
                    power_acc[zone]["secs"] += duration
                    power_acc[zone]["sum"] += val * duration

            prev_elapsed = curr_elapsed

        def finalize(acc):
            res = []
            for z, data in sorted(acc.items()):
                res.append({
                    "zoneNumber": z,
                    "secsInZone": round(data["secs"], 3),
                    "avgValue": round(data["sum"] / data["secs"], 2) if data["secs"] > 0 else 0,
                    "zoneLowBoundary": data["boundary"]
                })
            return res

        return finalize(hr_acc), finalize(power_acc), finalize(pace_acc)

    def fetch_activities(self, start_date: str, end_date: str) -> List[ActualActivity]:
        """Fetches activities between start_date and end_date (YYYY-MM-DD)."""
        logger.info(f"Fetching activities from {start_date} to {end_date}...")
        
        # Garmin API uses start and limit, so we fetch a batch and filter
        # For a 14-week plan, 100 activities should be plenty
        activities = self.client.get_activities(0, 100)
        
        filtered_activities = self.filter_activities(activities, start_date, end_date)
        
        logger.info(f"Found {len(filtered_activities)} activities in range.")
        return filtered_activities

    def save_actuals(self, activities: List[ActualActivity], file_path: str = "actuals.json"):
        """Saves the activities to a JSON file."""
        # Convert dataclasses to dicts for JSON serialization
        serializable_activities = [asdict(a) for a in activities]
        with open(file_path, "w") as f:
            json.dump(serializable_activities, f, indent=2)
        logger.info(f"Saved actuals to {file_path}")
        
        # Update context.json status
        try:
            with open("context.json", "r") as f:
                context = json.load(f)
            
            # Use AWST (UTC+8) for the update timestamp
            awst_now = get_awst_now()
            context["status"]["lastUpdated"] = awst_now.strftime("%Y-%m-%d")
            context["status"]["garminSync"] = f"Plan synced. {len(activities)} actuals recorded."
            
            with open("context.json", "w") as f:
                json.dump(context, f, indent=2)
            logger.info("Updated context.json status.")
        except Exception as e:
            logger.error(f"Failed to update context.json: {e}")

def get_awst_now():
    """Returns the current time in AWST (UTC+8)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8)

def main():
    fetcher = GarminActualsFetcher()
    
    # Use AWST (UTC+8) for "today"
    awst_now = get_awst_now()
    
    # Plan starts Jan 5, 2026. We'll fetch from then until today.
    start_date = "2026-01-05"
    end_date = awst_now.strftime("%Y-%m-%d")
    
    # If today is before the plan start, let's just fetch the last 7 days for testing
    if end_date < start_date:
        logger.info("Today is before plan start. Fetching last 7 days for testing purposes.")
        start_date = (awst_now - timedelta(days=7)).strftime("%Y-%m-%d")

    activities = fetcher.fetch_activities(start_date, end_date)
    fetcher.save_actuals(activities)

if __name__ == "__main__":
    main()
