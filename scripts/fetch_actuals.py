import json
import logging
import os
import sys
import base64
import zipfile
import io
import shutil
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from dotenv import load_dotenv
from garminconnect import Garmin

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.domain import ActualActivity

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
        
        # 1. Try token login (no creds needed if tokens are valid)
        try:
            # Attempt to init without creds to force token usage
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

    def filter_activities(self, activities: List[Dict[str, Any]], start_date: str, end_date: str) -> List[ActualActivity]:
        """Filters raw Garmin activities by date range and maps to our schema."""
        filtered_activities: List[ActualActivity] = []
        
        # Load pace thresholds from data/context.json
        pace_thresholds = []
        try:
            with open("data/context.json", "r") as f:
                context = json.load(f)
                pace_thresholds = context.get("runner", {}).get("trainingZones", {}).get("pace", [])
        except Exception as e:
            logger.warning(f"Could not load pace thresholds from data/context.json: {e}")

        for act in activities:
            # act['startTimeLocal'] is usually "2025-12-31 08:00:00"
            act_date_str = act['startTimeLocal'].split(' ')[0]
            
            if start_date <= act_date_str <= end_date:
                activity_id = act['activityId']
                hr_zones = []
                power_zones = []
                pace_zones = []

                # Fetch detailed zones for running/cycling/trail_running
                if act['activityType']['typeKey'] in ['running', 'cycling', 'trail_running']:
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
                        hr_zones = self.map_fallback_zones(raw_hr_summary, act['duration'])
                        power_zones = [] # self.map_fallback_zones(raw_power_summary) # Power ignored in schema for now

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

    def map_fallback_zones(self, zones: List[Dict], total_duration: float) -> List[Dict]:
        """Maps Garmin raw zones to API schema."""
        if not zones: return []
        res = []
        for z in zones:
            secs = z.get("secsInZone", 0)
            res.append({
                "zoneNumber": z.get("zoneNumber"),
                "secsInZone": secs,
                "zoneLow": z.get("zoneLowBoundary", 0),
                "zoneHigh": z.get("zoneHighBoundary", 0),
                "percentInZone": (secs / total_duration * 100.0) if total_duration > 0 else 0
            })
        return res

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
            # Pre-calculate highs for thresholds if needed (simplified: passed in usually)
            return {t[key_name]: {"secs": 0.0, "sum": 0.0, "boundary": t["lowBoundary"], "high": t.get("highBoundary", 999.0)} for t in thresholds}

        # Helper to add high boundaries to processed list
        def add_highs(proc_list):
            sorted_p = sorted(proc_list, key=lambda x: x["lowBoundary"])
            for i in range(len(sorted_p)):
                if i < len(sorted_p) - 1:
                    sorted_p[i]["highBoundary"] = sorted_p[i+1]["lowBoundary"]
                else:
                    sorted_p[i]["highBoundary"] = 999.0 # Infinity/Max
            return sorted_p

        # Format summaries/thresholds for processing
        pace_proc = [{"zone": t["zone"], "lowBoundary": t["lowBoundary_m_s"]} for t in pace_thresholds]
        pace_proc = add_highs(pace_proc)
        
        hr_proc = [{"zone": t["zoneNumber"], "lowBoundary": t["zoneLowBoundary"]} for t in hr_summary]
        hr_proc = add_highs(hr_proc)
        
        power_proc = [{"zone": t["zoneNumber"], "lowBoundary": t["zoneLowBoundary"]} for t in power_summary]
        power_proc = add_highs(power_proc)

        pace_acc = init_acc(pace_proc, "zone")
        hr_acc = init_acc(hr_proc, "zone")
        power_acc = init_acc(power_proc, "zone")

        prev_elapsed = 0.0
        total_dur_calc = 0.0
        
        for m in metrics:
            sm = m.get("metrics", [])
            curr_elapsed = sm[elapsed_idx] if len(sm) > elapsed_idx else None
            if curr_elapsed is None: continue
            
            duration = curr_elapsed - prev_elapsed
            if duration <= 0:
                prev_elapsed = curr_elapsed
                continue
            
            total_dur_calc += duration

            # Process Pace (ONLY for running/trail_running)
            if act_type in ['running', 'trail_running'] and speed_idx is not None and len(sm) > speed_idx and sm[speed_idx] is not None:
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

        def finalize(acc, duration_total):
            res = []
            for z, data in sorted(acc.items()):
                percent = (data["secs"] / duration_total * 100.0) if duration_total > 0 else 0
                res.append({
                    "zoneNumber": z,
                    "secsInZone": round(data["secs"], 3),
                    # "avgValue": round(data["sum"] / data["secs"], 2) if data["secs"] > 0 else 0, # Ignored by schema
                    "zoneLow": data["boundary"],
                    "zoneHigh": data["high"],
                    "percentInZone": round(percent, 2)
                })
            return res

        return finalize(hr_acc, total_dur_calc), [], [] # Only returning HR zones for now to match Schema strictness

    def fetch_activities(self, start_date: str, end_date: str) -> List[ActualActivity]:
        """Fetches activities between start_date and end_date (YYYY-MM-DD)."""
        logger.info(f"Fetching activities from {start_date} to {end_date}...")
        
        # Garmin API uses start and limit, so we fetch a batch and filter
        # For a 14-week plan, 100 activities should be plenty
        activities = self.client.get_activities(0, 100)
        
        filtered_activities = self.filter_activities(activities, start_date, end_date)
        
        logger.info(f"Found {len(filtered_activities)} activities in range.")
        return filtered_activities

    async def save_actuals(self, activities: List[ActualActivity]):
        """Saves the activities via API."""
        import httpx
        
        API_URL = "http://localhost:8000/api"
        # Convert dataclasses to dicts for JSON serialization
        serializable_activities = [asdict(a) for a in activities]
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{API_URL}/actuals", json=serializable_activities)
                if response.status_code == 200:
                    logger.info(f"Successfully synced {len(activities)} activities via API.")
                else:
                    logger.error(f"Failed to sync actuals. Status: {response.status_code}. Msg: {response.text}")
        except Exception as e:
            logger.error(f"API Connection Error: {e}")

def get_awst_now():
    """Returns the current time in AWST (UTC+8)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=8)

async def run_async():
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
    await fetcher.save_actuals(activities)

def main():
    import asyncio
    asyncio.run(run_async())

if __name__ == "__main__":
    main()
