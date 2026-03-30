import logging
import os
import base64
import zipfile
import io
import tempfile
import shutil
import uuid
from datetime import date, datetime
from typing import List, Dict, Any, Optional

from garminconnect import Garmin
from sqlmodel import Session, select

from app.models.domain import ActualActivity
from app.services.context import ContextService
from app.core.profile_sync import load_prefs, dump_prefs, can_write

logger = logging.getLogger(__name__)


class GarminService:
    def __init__(
        self, session: Optional[Session] = None, token_b64: Optional[str] = None
    ):
        self.session = session
        self.tokens_b64 = token_b64
        self.client = None
        self.temp_dir = None

        # Only attempt login if token is provided (stateless/frontend-driven)
        if self.tokens_b64:
            self._login()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp Garmin directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(
                    f"Failed to cleanup temp Garmin directory {self.temp_dir}: {e}"
                )
        self.temp_dir = None

    def _login(self):
        if self.tokens_b64:
            try:
                # Create a unique temp directory for this request session
                session_id = str(uuid.uuid4())
                self.temp_dir = os.path.join(
                    tempfile.gettempdir(), f"garth_session_{session_id}"
                )
                os.makedirs(self.temp_dir, exist_ok=True)

                self.tokens_b64 = self.tokens_b64.strip()

                # Decode and extract
                zip_data = base64.b64decode(self.tokens_b64)
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    zf.extractall(self.temp_dir)
                logger.debug(f"Restored Garmin tokens to temp dir: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to restore tokens: {e}")
                if self.temp_dir:
                    self.cleanup()
                return

        # 1. Try token login with the specific temp directory
        try:
            logger.info("Attempting login with provided tokens...")
            self.client = Garmin()
            # login(path) tells garth where to load tokens from
            self.client.login(self.temp_dir)
            logger.info(
                f"Successfully logged in with tokens as {self.client.display_name}"
            )
            return
        except Exception as e_token:
            logger.warning(f"Token login failed: {e_token}")
            self.client = None
            self.cleanup()

        # 2. Fallback to password login - REMOVED per user request
        # if not self.email or not self.password: ...

        # If we reach here and self.client is None, it means token login failed or no token provided.
        # We do not fallback to env vars anymore.
        if not self.client:
            logger.warning(
                "Garmin Service initialized but no valid token provided or token login failed."
            )

    @staticmethod
    def generate_tokens(email: str, password: str) -> str:
        # Create a unique temp directory for this login attempt to avoid collisions
        session_id = str(uuid.uuid4())
        # Use standard temp dir
        temp_dir = os.path.join(tempfile.gettempdir(), f"garth_{session_id}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Login
            client = Garmin(email, password)
            # Perform login without passing a path to avoid attempting to load non-existent/invalid tokens
            # This forces a fresh login using the provided credentials
            client.login()

            # Now save the tokens to our temp directory so we can zip them
            # garminconnect wraps garth, which handles the tokens
            if hasattr(client, "garth"):
                client.garth.dump(temp_dir)
            else:
                raise Exception("Garmin client does not expose garth attribute")

            # Zip the directory in memory

            # Zip the directory in memory
            bio = io.BytesIO()
            with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Archive name should be relative to temp_dir (e.g., 'oauth1_token')
                        arcname = os.path.relpath(file_path, temp_dir)
                        zf.write(file_path, arcname)

            return base64.b64encode(bio.getvalue()).decode("utf-8")
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise ValueError(f"Garmin login failed: {str(e)}")
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def fetch_user_profile(self, user_id: int) -> None:
        """
        Fetch the Garmin user profile and merge into RunnerProfile.

        Fields written (all gated by profile_sync_prefs):
          - birthday / age          userData.birthDate   (always, when unset)
          - gender                  userData.gender      (always, when unset)
          - weight_kg               userData.weight      pref: garmin.weight
          - height_cm               userData.height      pref: garmin.height
          - resting_hr              get_rhr_day()        pref: garmin.resting_hr
          - vo2max                  get_max_metrics()    pref: garmin.vo2max
          - lactate_threshold_hr/   get_lactate_threshold()
            lactate_threshold_pace                       pref: garmin.lactate_threshold

        Silently no-ops if the Garmin client is unavailable or the profile is missing.
        """
        if not self.client or not self.session:
            return

        try:
            from app.core.database import RunnerProfile

            profile = self.session.exec(
                select(RunnerProfile).where(RunnerProfile.user_id == user_id)
            ).first()
            if not profile:
                return

            prefs = load_prefs(profile.profile_sync_prefs_json)
            changed = False

            # ------------------------------------------------------------------
            # Basic user data (get_user_profile)
            # ------------------------------------------------------------------
            raw = self.client.get_user_profile()
            if raw:
                user_data = raw.get("userData", raw)

                # birthday / age — always write when unset (factual, no toggle)
                birth_str = user_data.get("birthDate")
                if birth_str and not profile.birthday:
                    try:
                        bday = date.fromisoformat(birth_str)
                        profile.birthday = bday
                        today = date.today()
                        profile.age = (
                            today.year
                            - bday.year
                            - ((today.month, today.day) < (bday.month, bday.day))
                        )
                        changed = True
                    except ValueError:
                        logger.warning(
                            f"Garmin unparseable birthDate '{birth_str}' for user {user_id}"
                        )

                # gender — always write when unset
                gender_raw = user_data.get("gender", "")
                if gender_raw and (not profile.gender or profile.gender == "unknown"):
                    gender_lower = gender_raw.lower()
                    if gender_lower in ("male", "female"):
                        profile.gender = gender_lower
                        changed = True

                # weight — pref-gated
                if can_write(prefs, "garmin", "weight"):
                    weight_g = user_data.get("weight")
                    if weight_g:
                        profile.weight_kg = round(float(weight_g) / 1000.0, 1)
                        changed = True

                # height — pref-gated; already in userData, just wasn't extracted before
                if can_write(prefs, "garmin", "height"):
                    height_raw = user_data.get("height")
                    if height_raw:
                        try:
                            profile.height_cm = int(height_raw)
                            changed = True
                        except (ValueError, TypeError):
                            pass

            # ------------------------------------------------------------------
            # Resting HR
            # ------------------------------------------------------------------
            if can_write(prefs, "garmin", "resting_hr"):
                try:
                    today_str = date.today().isoformat()
                    rhr_data = self.client.get_rhr_day(today_str)
                    # {"allMetrics": {"metricsMap": {"WELLNESS_RESTING_HEART_RATE": [{"value": N}]}}}
                    if rhr_data:
                        metrics_map = rhr_data.get("allMetrics", {}).get(
                            "metricsMap", {}
                        )
                        rhr_list = metrics_map.get("WELLNESS_RESTING_HEART_RATE", [])
                        if rhr_list:
                            rhr_val = rhr_list[0].get("value")
                            if rhr_val and int(rhr_val) > 0:
                                profile.resting_hr = int(rhr_val)
                                changed = True
                except Exception as e:
                    logger.debug(f"Garmin resting HR fetch failed (non-fatal): {e}")

            # ------------------------------------------------------------------
            # VO2Max
            # ------------------------------------------------------------------
            if can_write(prefs, "garmin", "vo2max"):
                try:
                    today_str = date.today().isoformat()
                    max_metrics = self.client.get_max_metrics(today_str)
                    if isinstance(max_metrics, list):
                        for entry in reversed(max_metrics):
                            vo2 = entry.get("generic", {}).get("vo2MaxValue")
                            if vo2 is not None:
                                profile.vo2max = float(vo2)
                                changed = True
                                break
                except Exception as e:
                    logger.debug(f"Garmin VO2Max fetch failed (non-fatal): {e}")

            # ------------------------------------------------------------------
            # Lactate threshold
            # ------------------------------------------------------------------
            if can_write(prefs, "garmin", "lactate_threshold"):
                try:
                    lt_data = self.client.get_lactate_threshold()
                    # {"lactateThresholdHeartRate": N, "lactateThresholdSpeed": N (m/s)}
                    if lt_data:
                        lt_hr = lt_data.get("lactateThresholdHeartRate")
                        lt_speed = lt_data.get("lactateThresholdSpeed")
                        if lt_hr and int(lt_hr) > 0:
                            profile.lactate_threshold_hr = int(lt_hr)
                            changed = True
                        if lt_speed and float(lt_speed) > 0:
                            profile.lactate_threshold_pace = float(lt_speed)
                            changed = True
                except Exception as e:
                    logger.debug(
                        f"Garmin lactate threshold fetch failed (non-fatal): {e}"
                    )

            # ------------------------------------------------------------------
            # Persist
            # ------------------------------------------------------------------
            if changed:
                profile.profile_last_synced_at = datetime.utcnow()
                self.session.add(profile)
                self.session.commit()
                logger.info(f"Garmin profile synced for user_id={user_id}")

        except Exception as e:
            logger.warning(
                f"Could not fetch Garmin user profile for user {user_id}: {e}"
            )

    def fetch_activities(
        self, start_date: str, end_date: str, user=None
    ) -> List[ActualActivity]:
        """Fetches activities between start_date and end_date (YYYY-MM-DD)."""
        logger.info(f"Fetching activities from {start_date} to {end_date}...")

        # Garmin API uses start and limit, so we fetch a batch and filter
        # For a 14-week plan, 100 activities should be plenty
        activities = self.client.get_activities(0, 100)

        filtered_activities = self.filter_activities(
            activities, start_date, end_date, user=user
        )

        logger.info(f"Found {len(filtered_activities)} activities in range.")
        return filtered_activities

    def filter_activities(
        self,
        activities: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        user=None,
    ) -> List[ActualActivity]:
        """Filters raw Garmin activities by date range and maps to our schema."""
        filtered_activities: List[ActualActivity] = []

        # Load pace thresholds from DB or Session
        pace_thresholds = []
        if self.session and user:
            try:
                ctx_service = ContextService(self.session)
                ctx = ctx_service.get_context(user=user)
                if ctx.runner.trainingZones and ctx.runner.trainingZones.pace:
                    pace_thresholds = [
                        z.model_dump() for z in ctx.runner.trainingZones.pace
                    ]
            except Exception as e:
                logger.warning(f"Could not load pace thresholds from DB: {e}")

        for act in activities:
            # Extract date part from YYYY-MM-DD HH:MM:SS format
            act_date_str = act["startTimeLocal"].split(" ")[0]

            if start_date <= act_date_str <= end_date:
                activity_id = act["activityId"]
                hr_zones = []
                power_zones = []
                pace_zones = []
                splits = []

                # Fetch detailed zones for running/cycling/trail_running
                if act["activityType"]["typeKey"] in [
                    "running",
                    "cycling",
                    "trail_running",
                ]:
                    # Get Splits
                    try:
                        splits_result = self.client.get_activity_splits(activity_id)
                        if splits_result and isinstance(splits_result, dict):
                            logger.info(
                                f"Splits keys for {activity_id}: {list(splits_result.keys())}"
                            )
                            if "lapSplits" in splits_result:
                                splits = splits_result["lapSplits"]
                            elif "splits" in splits_result:
                                splits = splits_result["splits"]
                            else:
                                # Fallback: check if we can find a list property that looks like splits
                                found_list = next(
                                    (
                                        v
                                        for k, v in splits_result.items()
                                        if isinstance(v, list) and len(v) > 0
                                    ),
                                    [],
                                )
                                splits = found_list
                        elif isinstance(splits_result, list):
                            splits = splits_result
                        else:
                            splits = []
                    except Exception as e:
                        logger.warning(f"Could not fetch splits for {activity_id}: {e}")
                        splits = []

                    # Try to get existing summaries to use as boundaries
                    raw_hr_summary = []
                    raw_power_summary = []
                    try:
                        raw_hr_summary = self.client.get_activity_hr_in_timezones(
                            activity_id
                        )
                    except Exception as e:
                        logger.debug(
                            f"Could not fetch HR summary for {activity_id}: {e}"
                        )

                    try:
                        raw_power_summary = self.client.connectapi(
                            f"activity-service/activity/{activity_id}/powerTimeInZones"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Could not fetch power summary for {activity_id}: {e}"
                        )

                    # Enrich zones with averages from telemetry
                    try:
                        hr_zones, power_zones, pace_zones = (
                            self.enrich_zones_with_telemetry(
                                activity_id,
                                act["activityType"]["typeKey"],
                                pace_thresholds,
                                raw_hr_summary,
                                raw_power_summary,
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to enrich zones for {activity_id}: {e}")
                        # Fallback to summaries if telemetry fails
                        hr_zones = self.map_fallback_zones(
                            raw_hr_summary, act["duration"]
                        )
                        power_zones = []

                filtered_activities.append(
                    ActualActivity(
                        date=act_date_str,
                        name=act["activityName"],
                        type=act["activityType"]["typeKey"],
                        distance_m=act["distance"],
                        duration_s=act["duration"],
                        average_pace_m_s=act.get("averageSpeed"),
                        average_hr=act.get("averageHR"),
                        max_hr=act.get("maxHR"),
                        average_power=act.get("avgPower"),
                        aerobic_te=act.get("aerobicTrainingEffect"),
                        anaerobic_te=act.get("anaerobicTrainingEffect"),
                        training_load=act.get("activityTrainingLoad"),
                        calories=act.get("calories"),
                        activityId=activity_id,
                        hr_zones=hr_zones,
                        power_zones=power_zones,
                        pace_zones=pace_zones,
                        splits=splits,
                    )
                )
        return filtered_activities

    def map_fallback_zones(
        self, zones: List[Dict], total_duration: float
    ) -> List[Dict]:
        """Maps Garmin raw zones to API schema."""
        if not zones:
            return []
        res = []
        for z in zones:
            secs = z.get("secsInZone", 0)
            res.append(
                {
                    "zoneNumber": z.get("zoneNumber"),
                    "secsInZone": secs,
                    "zoneLow": z.get("zoneLowBoundary", 0),
                    "zoneHigh": z.get("zoneHighBoundary", 0),
                    "percentInZone": (secs / total_duration * 100.0)
                    if total_duration > 0
                    else 0,
                }
            )
        return res

    def enrich_zones_with_telemetry(
        self,
        activity_id: int,
        act_type: str,
        pace_thresholds: List[Dict],
        hr_summary: List[Dict],
        power_summary: List[Dict],
    ):
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
            # Initialize accumulator dictionary for each zone threshold
            return {
                t[key_name]: {
                    "secs": 0.0,
                    "sum": 0.0,
                    "boundary": t["lowBoundary"],
                    "high": t.get("highBoundary", 999.0),
                }
                for t in thresholds
            }

        # Helper to add high boundaries to processed list
        def add_highs(proc_list):
            sorted_p = sorted(proc_list, key=lambda x: x["lowBoundary"])
            for i in range(len(sorted_p)):
                if i < len(sorted_p) - 1:
                    sorted_p[i]["highBoundary"] = sorted_p[i + 1]["lowBoundary"]
                else:
                    sorted_p[i]["highBoundary"] = 999.0  # Upper bound
            return sorted_p

        # Format summaries/thresholds for processing
        pace_proc = [
            {"zone": t["zone"], "lowBoundary": t["lowBoundary_m_s"]}
            for t in pace_thresholds
        ]
        pace_proc = add_highs(pace_proc)

        hr_proc = [
            {"zone": t["zoneNumber"], "lowBoundary": t["zoneLowBoundary"]}
            for t in hr_summary
        ]
        hr_proc = add_highs(hr_proc)

        power_proc = [
            {"zone": t["zoneNumber"], "lowBoundary": t["zoneLowBoundary"]}
            for t in power_summary
        ]
        power_proc = add_highs(power_proc)

        pace_acc = init_acc(pace_proc, "zone")
        hr_acc = init_acc(hr_proc, "zone")
        power_acc = init_acc(power_proc, "zone")

        prev_elapsed = 0.0
        total_dur_calc = 0.0

        for m in metrics:
            sm = m.get("metrics", [])
            curr_elapsed = sm[elapsed_idx] if len(sm) > elapsed_idx else None
            if curr_elapsed is None:
                continue

            duration = curr_elapsed - prev_elapsed
            if duration <= 0:
                prev_elapsed = curr_elapsed
                continue

            total_dur_calc += duration

            # Process Pace (ONLY for running/trail_running)
            if (
                act_type in ["running", "trail_running"]
                and speed_idx is not None
                and len(sm) > speed_idx
                and sm[speed_idx] is not None
            ):
                val = sm[speed_idx]
                zone = 0
                for t in sorted(
                    pace_proc, key=lambda x: x["lowBoundary"], reverse=True
                ):
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
            if (
                power_idx is not None
                and len(sm) > power_idx
                and sm[power_idx] is not None
            ):
                val = sm[power_idx]
                zone = 0
                for t in sorted(
                    power_proc, key=lambda x: x["lowBoundary"], reverse=True
                ):
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
                percent = (
                    (data["secs"] / duration_total * 100.0) if duration_total > 0 else 0
                )
                res.append(
                    {
                        "zoneNumber": z,
                        "secsInZone": round(data["secs"], 3),
                        "avgValue": round(data["sum"] / data["secs"], 2)
                        if data["secs"] > 0
                        else 0,
                        "zoneLow": data["boundary"],
                        "zoneHigh": data["high"],
                        "percentInZone": round(percent, 2),
                    }
                )
            return res

        return (
            finalize(hr_acc, total_dur_calc),
            finalize(power_acc, total_dur_calc),
            finalize(pace_acc, total_dur_calc),
        )
