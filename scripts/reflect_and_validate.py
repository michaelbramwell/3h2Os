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
from sqlmodel import Session, select

# Types that contribute to the "Hard" portion of 80/20 rule
INTENSITY_TYPES = ["interval", "intervals", "tempo", "threshold", "steady", "race", "fartlek", "hill", "hills"]

def parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")

def get_week_start(date_str: str) -> str:
    dt = parse_date(date_str)
    start = dt - timedelta(days=dt.weekday())
    return start.strftime("%Y-%m-%d")

def load_actuals_as_weeks(filepath: str) -> Dict[str, Week]:
    if not os.path.exists(filepath):
        return {}

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
        
    return weeks

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
        with Session(engine) as session:
            # Check for user 'mike'
            user = session.exec(select(User).where(User.username == "mike")).first()
            
            if not user:
                # Create user if missing (helpful for fresh setups)
                print("User 'mike' not found. Creating...")
                user = User(username="mike", email="mike@example.com")
                session.add(user)
                session.commit()
                session.refresh(user)

            # Deactivate all current active plans
            active_plans = session.exec(select(RunnerPlan).where(RunnerPlan.user_id == user.id).where(RunnerPlan.is_active == True)).all()
            if active_plans:
                print(f"Archiving {len(active_plans)} active plan(s)...")
                for p in active_plans:
                    p.is_active = False
                    session.add(p)
            
            # Create new active plan
            print("Creating new active plan version...")
            new_plan = RunnerPlan(
                title=f"Plan Update {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                is_active=True,
                plan_json=json.dumps(data),
                user_id=user.id
            )
            session.add(new_plan)
            session.commit()
            print("Database updated with new version!")

    except Exception as e:
        print(f"Warning: Database update failed: {e}")

def set_workout_distance(workout: Workout, new_dist_m: float):
    old_dist_km = workout.distance_m / 1000
    new_dist_km = new_dist_m / 1000
    
    workout.distance_m = new_dist_m
    
    # Attempt to update name if it starts with "Xk " or "X.Yk "
    # Regex for "8k", "8.5k", "10k" at start of string
    match = re.match(r"^(\d+(\.\d+)?)k\s", workout.name, re.IGNORECASE)
    if match:
        original_str = match.group(0) # e.g. "8k "
        # We replace it if it looks like a distance prefix
        new_str = f"{new_dist_km:.1f}k "
        workout.name = workout.name.replace(original_str, new_str, 1)
    else:
        # Append (Adj) if not already there
        if "(Adj)" not in workout.name:
             workout.name += " (Adj)"

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
    actual_weeks = load_actuals_as_weeks(actuals_path)
    print(f"Loading plan from {plan_path}...")
    planned_weeks = load_plan(plan_path)
    
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

    print(f"\nChecking plan progression from {next_start_str}...")
    
    # Initialize the "Previous Volume" with the Actuals
    prev_vol = vol 
    
    changes_made = False
    
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
        
        if has_race:
             prev_vol = curr_vol
             continue

        # Rule 1: Volume Cap vs Previous Week
        # If prev_vol is 0 (coming off a rest week or break), we might need special handling
        # But assuming normal progression:
        if prev_vol > 0:
            ratio = curr_vol / prev_vol
            max_ratio = validator.max_volume_increase_ratio # 1.15
            
            if ratio > max_ratio:
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
