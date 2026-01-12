import json
import os
import sys
import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from dataclasses import asdict

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.models.domain import Week, Day, Workout, GarminActivityType
from app.core.validation import ValidationEngine
from app.core.database import engine, RunnerPlan, User
from app.core.services import save_plan_to_db
from sqlmodel import Session, select

# Types that contribute to the "Hard" portion of 80/20 rule
INTENSITY_TYPES = ["interval", "intervals", "tempo", "threshold", "steady", "race", "fartlek", "hill", "hills"]

def parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")

def get_week_start(date_str: str) -> str:
    dt = parse_date(date_str)
    start = dt - timedelta(days=dt.weekday())
    return start.strftime("%Y-%m-%d")

def has_race_workout(week: Week) -> bool:
    """Check if a week contains any race workouts."""
    for day in week.days.values():
        for workout in day.workouts:
            if "race" in workout.type.lower():
                return True
    return False

def load_actuals_as_weeks(filepath: str) -> Tuple[Dict[str, Week], Dict[str, bool]]:
    """Load actual weeks and pre-compute race flags for optimization.
    
    Returns:
        Tuple of (weeks_dict, race_flags_dict) where race_flags_dict maps
        week_start -> bool indicating if that week has a race workout.
    """
    if not os.path.exists(filepath):
        return {}, {}

    with open(filepath, 'r') as f:
        data = json.load(f)
    
    weeks = {}
    
    for activity in data:
        # Filter: Only include running and trail running
        vocab_type = activity.get('type', '').lower()
        if vocab_type not in [GarminActivityType.RUNNING.value, GarminActivityType.TRAIL_RUNNING.value]:
            continue

        w_start = get_week_start(activity['date'])
        
        if w_start not in weeks:
            weeks[w_start] = Week(weekStarting=w_start, days={})
        
        # Convert to local format
        workout = Workout(
            name=activity.get('name', 'Run'),
            type=activity.get('type', 'Run'),
            distance_m=activity.get('distance_m', 0),
            timeOfDay="AM"
        )
        
        day_date = activity['date']
        dt = parse_date(day_date)
        day_name = dt.strftime("%a")
        
        if day_name not in weeks[w_start].days:
            weeks[w_start].days[day_name] = Day(date=day_date, workouts=[])
            
        weeks[w_start].days[day_name].workouts.append(workout)
    
    # Pre-compute race flags for each week to avoid nested loops later
    race_flags = {week_start: has_race_workout(week) for week_start, week in weeks.items()}
    
    return weeks, race_flags

def load_plan(filepath: str) -> List[Week]:
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        data = json.load(f)
    return [Week.from_dict(w) for w in data]

def save_plan(weeks: List[Week], filepath: str):
    # 1. Save to JSON File
    data = [asdict(w) for w in weeks]
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    # 2. Save to Database (With History)
    try:
        print("Saving to database via service...")
        with Session(engine) as session:
            save_plan_to_db(data, session, username="mike")
        print("Database updated with new version!")
    except Exception as e:
        print(f"Warning: Failed to save plan to database for user 'mike' while processing '{filepath}': {e!r}")

def set_workout_distance(workout: Workout, new_dist_m: float):
    # Determine if we should round closely (Training runs = Integer km, Races = Float km)
    is_race = "race" in workout.type.lower()

    if not is_race:
        # Snap to nearest KM to ensure "Name matches Data" prevents total discrepancies
        rounded_km = round(new_dist_m / 1000.0)
        final_dist_m = rounded_km * 1000.0
    else:
        final_dist_m = new_dist_m
    
    workout.distance_m = final_dist_m
    final_dist_km = final_dist_m / 1000.0
    
    # Attempt to update name if it starts with "Xk " or "X.Yk "
    # Regex for "8k", "8.5k", "10k" at start of string
    match = re.match(r"^(\d+(\.\d+)?)k\s", workout.name, re.IGNORECASE)
    if match:
        original_str = match.group(0) # e.g. "8k "
        
        # Format based on type: Integers for training runs, Decimals for Races
        if is_race:
            new_str = f"{final_dist_km:.1f}k "
        else:
            new_str = f"{final_dist_km:.0f}k "
            
        workout.name = workout.name.replace(original_str, new_str, 1)
    
    # Remove (Adj) if present, as user requested not to use it
    if "(Adj)" in workout.name:
        workout.name = workout.name.replace(" (Adj)", "")

def calculate_intensity_volume(week: Week) -> float:
    # Use global INTENSITY_TYPES
    total = 0
    if not week.days:
        return 0
    for day in week.days.values():
        for w in day.workouts:
            w_type = w.type.lower()
            if any(t in w_type for t in INTENSITY_TYPES):
                total += w.distance_m
    return total

def main():
    actuals_path = "data/actuals.json"
    plan_path = "data/plan.json"
    
    # Fallback to root if data/ not found (for testing etc)
    if not os.path.exists(actuals_path): actuals_path = "actuals.json"
    if not os.path.exists(plan_path): plan_path = "plan.json"
    
    print(f"Loading actuals from {actuals_path}...")
    actual_weeks, race_flags = load_actuals_as_weeks(actuals_path)
    print(f"Loading plan from {plan_path}...")
    planned_weeks = load_plan(plan_path)

    changes_made = False # Track changes globally

    # Normalize workout names (apply rounding rules)
    for week in planned_weeks:
        for day in week.days.values():
            for workout in day.workouts:
                old_name = workout.name
                set_workout_distance(workout, workout.distance_m)
                if workout.name != old_name:
                    changes_made = True
    
    if changes_made:
        print(" -> Applied name formatting updates.")
    
    validator = ValidationEngine()
    
    print("\n--- Reflection, Guardrails & Adjustment Engine ---")
    
    # Sort actual weeks
    sorted_starts = sorted(actual_weeks.keys())
    if not sorted_starts:
        print("No actual weeks data found.")
        return
        
    last_actual_week_start = sorted_starts[-1]
    last_actual_week = actual_weeks[last_actual_week_start]
    
    print(f"\nLatest Completed Week (Start: {last_actual_week_start})")
    vol = validator._calculate_volume(last_actual_week)
    print(f"   Actual Volume: {vol/1000:.2f} km")
    
    # Determine implied previous volume for validation baseline
    # If the last actual week was a Rest/Race/Marathon week, its volume is artificially low/irregular.
    # We should look back to find the last "Normal" week's volume to use as the baseline cap for future weeks.
    validation_baseline_vol = vol

    last_completed_plan_week = next((w for w in planned_weeks if w.weekStarting == last_actual_week_start), None)
    
    if last_completed_plan_week:
        last_status = getattr(last_completed_plan_week, "status", "normal").lower()
        
        # Use pre-computed race flag instead of nested loops
        last_actual_had_race = race_flags.get(last_actual_week_start, False)

        if last_status in ["rest", "recovery", "race", "marathon"] or last_actual_had_race:
            print(f"   Last week was '{last_status}' (or Race). Looking back for volume baseline...")
            
            found_baseline = False
            for i in range(len(sorted_starts) - 2, -1, -1):
                past_week_start = sorted_starts[i]
                past_week_actual = actual_weeks[past_week_start]
                past_plan_week = next((w for w in planned_weeks if w.weekStarting == past_week_start), None)
                
                if not past_plan_week: continue 
                
                past_status = getattr(past_plan_week, "status", "normal").lower()
                # Use pre-computed race flag instead of nested loops
                past_had_race = race_flags.get(past_week_start, False)
                
                if past_status not in ["rest", "recovery", "race", "marathon"] and not past_had_race:
                    past_vol = validator._calculate_volume(past_week_actual)
                    if past_vol > 0:
                        validation_baseline_vol = past_vol
                        found_baseline = True
                        print(f"   -> Found baseline: Week {past_week_start} ({past_vol/1000:.1f} km)")
                        break
            
            if not found_baseline:
                print("   -> No normal baseline found in history. Using current volume.")

    # Check for baseline shift (Actual vs Plan for the COMPLETED week)
    match_index = next((i for i, w in enumerate(planned_weeks) if w.weekStarting == last_actual_week_start), None)
    if match_index is not None:
        planned_vol_last = validator._calculate_volume(planned_weeks[match_index])
        if planned_vol_last > 0:
            scaling_factor = vol / planned_vol_last
            # If actuals > 105% of plan, shift the future baseline up
            if scaling_factor > 1.05:
                print(f"   Detected volume increase vs plan (Ratio: {scaling_factor:.2f}). Scaling future weeks up...")
                # Apply scaling to ALL future weeks in memory before validation
                # note: start validation from match_index + 1
                for k in range(match_index + 1, len(planned_weeks)):
                     wk = planned_weeks[k]
                     for d in wk.days.values():
                         for w in d.workouts:
                             # Protect marathon/race workouts (e.g. "BUNBURY 42.2k") from being scaled
                             workout_name = (getattr(w, "name", "") or "").lower()
                             if "42.2" in workout_name or "marathon" in workout_name:
                                 continue
                             set_workout_distance(w, w.distance_m * scaling_factor)
                changes_made = True # Ensure we save even if validation doesn't trigger

    # --- Adjustment Logic ---
    
    # 1. Start iterating from the week AFTER the last actual week
    last_dt = parse_date(last_actual_week_start)
    next_start_dt = last_dt + timedelta(days=7)
    next_start_str = next_start_dt.strftime("%Y-%m-%d")
    
    # Find index of next week in plan
    start_index = next((i for i, w in enumerate(planned_weeks) if w.weekStarting == next_start_str), None)
    
    if start_index is None:
        print(f"No future plan found starting {next_start_str}")
        return

    # Initialize the "Previous Volume" with the Actuals
    prev_vol = vol 
    
    # Flag to allow manual override for the first future week
    manual_override_active = False

    # Check for MANUAL baseline shift (Disk vs DB for the CURRENT/NEXT week)
    # We look at Active Plan first. If that matches Disk, we check the most recent Archived (Inactive) plan.
    try:
        with Session(engine) as session:
             # Find user mike
             user = session.exec(select(User).where(User.username == "mike")).first()
             if user:
                 # 1. Get Comparisons
                 plans_to_check = []
                 
                 active_plan = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == user.id).where(RunnerPlan.is_active == True)).first()
                 if active_plan:
                     plans_to_check.append(active_plan)
                 
                 # Also fetch latest inactive plan
                 last_archived = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == user.id).where(RunnerPlan.is_active == False).order_by(RunnerPlan.created_at.desc())).first()
                 if last_archived:
                     plans_to_check.append(last_archived)

                 detected_scaling = False
                 
                 for db_plan_obj in plans_to_check:
                     if detected_scaling: break
                     
                     db_plan_data = json.loads(db_plan_obj.plan_json)
                     # Find the matching week in DB data
                     db_week_data = next((w for w in db_plan_data if w.get('weekStarting') == next_start_str), None)
                     
                     if db_week_data:
                         db_week = Week.from_dict(db_week_data)
                         db_vol = validator._calculate_volume(db_week)
                         disk_vol = validator._calculate_volume(planned_weeks[start_index])
                         
                         if db_vol > 0:
                             manual_ratio = disk_vol / db_vol
                             
                             # Scale future weeks if manual volume increase > 5% vs archived plan
                             if manual_ratio > 1.05:
                                 print(f"   Detected MANUAL volume increase vs DB Plan {db_plan_obj.id} (Ratio: {manual_ratio:.2f}). Scaling subsequent weeks...")
                                 for k in range(start_index + 1, len(planned_weeks)):
                                     wk = planned_weeks[k]
                                     for d in wk.days.values():
                                         for w in d.workouts:
                                             # Skip scaling marathon-distance workouts (e.g., key races)
                                             if getattr(w, "distance_m", None) is None:
                                                 continue
                                             if w.distance_m >= 42000:
                                                 continue
                                             set_workout_distance(w, w.distance_m * manual_ratio)
                                 changes_made = True
                                 manual_override_active = True
                                 detected_scaling = True

    except Exception as e:
        print(f"   Warning: Could not check DB for manual edits: {e}")

    print(f"\nChecking plan progression from {next_start_str}...")
    
    # Initialize the "Previous Volume" with the calculated baseline (ignoring recent Rest/Race dips)
    prev_vol = validation_baseline_vol 
    
    # Logic note: changes_made might already be True from baseline shifting
    
    for i in range(start_index, len(planned_weeks)):
        current_week = planned_weeks[i]
        curr_vol = validator._calculate_volume(current_week)
        
        # SKIP empty weeks (tapers/zeros) to prevent division by zero or weird scaling
        if curr_vol == 0:
            prev_vol = 0 
            continue
            
        original_vol = curr_vol
        week_changed = False
        
        # Check if week has a Race - Skip validation rules for Race weeks
        has_race = False
        if current_week.days:
             for d in current_week.days.values():
                 for w in d.workouts:
                      if "race" in w.type.lower():
                           has_race = True
                           break
                 if has_race: break
        
        week_status = getattr(current_week, "status", "normal").lower()
        
        # Bypass rules if status is 'taper' or 'rest' (or has race)
        if has_race or week_status in ["taper", "rest", "recovery", "marathon"]:
             print(f"  [Week {current_week.weekStarting}] Status '{week_status}' (or Race). Skipping increase validation.")
             
             # Verify purposeful volume reduction in rest/recovery weeks
             if week_status in ["rest", "recovery"] and prev_vol > 0:
                 if curr_vol > prev_vol * 0.9: # Warn if volume is not actually lower
                     print(f"    Warning: Rest week volume ({curr_vol/1000:.1f}k) is not significantly lower than previous ({prev_vol/1000:.1f}k).")
             
             # Determines baseline volume logic for subsequent weeks:
             # - Taper: Commits the drop (future weeks build from this new lower base)
             # - Rest/Race: Ignores the drop (future weeks compare against the last 'normal' build week)
             
             if week_status in ["taper"]:
                 prev_vol = curr_vol 
             elif week_status in ["rest", "recovery", "race"] or has_race:
                 pass 
             else:
                 prev_vol = curr_vol # Other bypassed types (e.g. marathon)
             
             continue

        # Rule 1: Volume Cap vs Previous Week
        # If prev_vol is 0 (coming off a rest week or break), we might need special handling
        # But assuming normal progression:
        if prev_vol > 0:
            # Skip check for the first week IF manual override was detected
            skip_rule_1 = (i == start_index and manual_override_active)
            
            ratio = curr_vol / prev_vol
            max_ratio = validator.max_volume_increase_ratio # 1.15
            
            if ratio > max_ratio and not skip_rule_1:
                # Violation!
                allowed_vol = prev_vol * max_ratio
                scaling = allowed_vol / curr_vol
                
                # Check for convergence (ignore < 1% change)
                if abs(1.0 - scaling) < 0.01:
                    continue

                print(f"  [Week {current_week.weekStarting}] Volume spike ({curr_vol/1000:.1f}km vs Prev {prev_vol/1000:.1f}km). Reducing by {(1-scaling)*100:.1f}%")
                
                for d in current_week.days.values():
                    for w in d.workouts:
                         # Use helper to scale all runs in week
                         new_m = w.distance_m * scaling
                         set_workout_distance(w, new_m)
                
                curr_vol = allowed_vol # Update for next iteration
                week_changed = True
                changes_made = True

        # Rule 2: Intensity Cap (80/20 Rule)
        # We check the INTENSITY volume ratio against the NEW total volume
        int_vol = calculate_intensity_volume(current_week)
        # Recalculate total vol just in case
        curr_vol_fresh = validator._calculate_volume(current_week)
        
        if curr_vol_fresh > 0:
            int_ratio = int_vol / curr_vol_fresh
            max_int_ratio = validator.max_intensity_ratio # 0.25 (or 0.3 depending on implementation)
            
            if int_ratio > max_int_ratio:
                 allowed_int_vol = curr_vol_fresh * max_int_ratio
                 int_scaling = allowed_int_vol / int_vol

                 # Check for convergence (ignore < 1% change)
                 if abs(1.0 - int_scaling) < 0.01:
                     # Update curr_vol ref even if we skip changes
                     prev_vol = curr_vol_fresh
                     continue
                 
                 print(f"  [Week {current_week.weekStarting}] High Intensity ({int_ratio*100:.1f}%). Reducing intensity workouts by {(1-int_scaling)*100:.1f}%")
                 
                 lost_distance = 0
                 
                 # Scale ONLY intensity workouts
                 for d in current_week.days.values():
                    for w in d.workouts:
                         w_type = w.type.lower()
                         # Don't scale the Race itself!
                         if "race" in w_type:
                             continue
                         if any(t in w_type for t in INTENSITY_TYPES):
                              old_m = w.distance_m
                              new_m = old_m * int_scaling
                              set_workout_distance(w, new_m)
                              lost_distance += (old_m - new_m)
                 
                 # Redistribute lost distance to Easy runs to maintain volume
                 if lost_distance > 0:
                     easy_runs = []
                     for d in current_week.days.values():
                         for w in d.workouts:
                             w_type = w.type.lower()
                             is_intensity = any(t in w_type for t in INTENSITY_TYPES)
                             is_race = "race" in w_type
                             if not is_intensity and not is_race:
                                 easy_runs.append(w)
                     
                     if easy_runs:
                          add_per_run = lost_distance / len(easy_runs)
                          print(f"    -> Reallocating {lost_distance/1000:.1f}km to {len(easy_runs)} easy runs ({add_per_run/1000:.1f}km each)")
                          for w in easy_runs:
                               set_workout_distance(w, w.distance_m + add_per_run)
                     else:
                          print("    -> No easy runs found. Volume will drop.")

                 week_changed = True
                 changes_made = True
                 # Update curr_vol again (should be same as curr_vol_fresh roughly)
                 curr_vol = validator._calculate_volume(current_week)

        # Update reference for next week
        prev_vol = curr_vol

    if changes_made:
        print("\nSaving updated plan to plan.json...")
        save_plan(planned_weeks, plan_path)
        print("Done.")
    else:
        print("\nNo changes required. Plan validates successfully.")

if __name__ == "__main__":
    main()
