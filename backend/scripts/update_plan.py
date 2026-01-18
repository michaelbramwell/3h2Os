import json
import os
import sys
import re
from datetime import datetime, timedelta
from typing import List
from dataclasses import asdict

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.models.domain import Week
from app.core.services import save_plan_to_db
from app.core.database import engine
from sqlmodel import Session

# --- Configuration ---
def get_current_week_start_str() -> str:
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    return start.strftime("%Y-%m-%d")

CURRENT_WEEK_START = get_current_week_start_str() # Defaults to current week
BASE_VOLUME_KM = 62.0 # Starting baseline volume for "Normal" weeks (approx Week 2/3 level)
MAX_VOLUME_INCREASE = 1.10 # 10% max increase per week
INTENSITY_RATIO = 0.20 # 80/20 rule target
LONG_RUN_RATIO = 0.30 # Approx 30% of weekly volume for long run

# Hard types for intensity calculation
INTENSITY_TYPES = ["interval", "intervals", "tempo", "threshold", "steady", "race", "fartlek", "hill", "hills", "plr"]

def parse_date(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d")

def load_plan(filepath: str) -> List[Week]:
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return []
    with open(filepath, 'r') as f:
        data = json.load(f)
    return [Week.from_dict(w) for w in data]

def save_plan(weeks: List[Week], filepath: str):
    data = [asdict(w) for w in weeks]
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Saved plan to {filepath}")
    
    # Also save to DB
    try:
        with Session(engine) as session:
            save_plan_to_db(data, session, username="mike")
    except Exception as e:
        print(f"DB Save Warning: {e}")

def get_week_volume(week: Week) -> float:
    total = 0
    for day in week.days.values():
        for w in day.workouts:
            total += w.distance_m
    return total

def set_week_volume(week: Week, target_vol_m: float):
    current_vol = get_week_volume(week)
    if current_vol == 0: return

    scale = target_vol_m / current_vol
    
    for day in week.days.values():
        for workout in day.workouts:
            # Race weeks: Don't scale the Race itself if possible? 
            # Actually for a bulk re-calc, we probably want to scale everything 
            # EXCEPT fixed distance races (like 42.2k). 
            # But for training races (like "10k Race"), maybe we leave them?
            
            # Heuristic: If it's a Marathon, don't scale it.
            if "marathon" in workout.name.lower() or "42.2" in workout.name:
                continue
                
            new_dist = workout.distance_m * scale
            
            # Snap to nearest 1km for cleanliness, unless it's very short
            # But keep races precise?
            if "race" in workout.type.lower():
                workout.distance_m = new_dist # Keep precision
            else:
                 # Round to nearest 500m or 1km
                workout.distance_m = round(new_dist / 1000) * 1000
            
            # Update name
            km_val = workout.distance_m / 1000
            # Regex to replace "8k", "8.5k" at start
            if re.match(r"^\d+(\.\d+)?k\s", workout.name, re.IGNORECASE):
                # Clean old prefix
                parts = workout.name.split(' ', 1)
                if len(parts) > 1:
                    suffix = parts[1]
                    # formatting: int if whole number, else preserve decimal precision
                    if km_val.is_integer():
                        workout.name = f"{int(km_val)}k {suffix}"
                    else:
                        workout.name = f"{km_val:g}k {suffix}"

def recalculate_plan():
    plan_path = "data/plan.json"
    weeks = load_plan(plan_path)
    
    # 1. Find index of current week to start from
    start_index = next((i for i, w in enumerate(weeks) if w.weekStarting == CURRENT_WEEK_START), None)
    if start_index is None:
        print("Could not find start week.")
        return

    print(f"Starting recalculation from Week {CURRENT_WEEK_START}...")
    
    # Baseline tracker
    current_baseline_vol = BASE_VOLUME_KM * 1000 # m
    
    # We iterate from current week to end
    for i in range(start_index, len(weeks)):
        week = weeks[i]
        status = getattr(week, "status", "normal").lower()
        
        # Determine if this week has a specific Race Distance set that shouldn't be touched?
        # For now, we assume the mix of workouts determines the volume distribution, 
        # and we just scale the totals.
        
        has_race = False
        for d in week.days.values():
            for w in d.workouts:
                if "race" in w.type.lower(): 
                    has_race = True
        
        target_vol = 0
        
        if status == "normal" and not has_race:
            # Build phase: Increase baseline
            # We want a slow progressive build.
            # E.g. +5% every normal week?
            # Or sticking to the rule of <10%
            
            # Increased to 7% per user request
            build_factor = 1.07
            
            # Start from previous baseline
            target_vol = current_baseline_vol * build_factor
            
            # Update baseline for next time
            current_baseline_vol = target_vol
            
            print(f"[Week {i+1} {week.weekStarting}] NORMAL: Building to {target_vol/1000:.1f}k")
            set_week_volume(week, target_vol)
            
        elif status in ["rest", "recovery"]:
            # Drop volume significantly (e.g. 60-70% of current baseline)
            drop_factor = 0.65
            target_vol = current_baseline_vol * drop_factor
            
            # DO NOT update baseline (next week resumes from where we were)
            print(f"[Week {i+1} {week.weekStarting}] REST: Dropping to {target_vol/1000:.1f}k")
            set_week_volume(week, target_vol)
            
        elif status == "taper":
            # Taper logic: Rapid reduction
            # Week 1 of taper: 70% of peak
            # Week 2 of taper: 40% of peak (Race Week usually)
            
            # Simple heuristic based on timeline position?
            # Let's just assume Taper weeks drop 20% from PREVIOUS week
            # But usually Taper is explicitly defined.
            
            # Let's just hold it at 60% of Baseline
            target_vol = current_baseline_vol * 0.60
            print(f"[Week {i+1} {week.weekStarting}] TAPER: Reduced to {target_vol/1000:.1f}k")
            set_week_volume(week, target_vol)
            
        elif status == "race" or has_race:
             # Race week volume depends on the race distance + limited easy running
             # We generally accept whatever is planned, but maybe check it's not huge?
             # Or we calculate it based on 50% baseline + Race distance?
             
             # For now, let's TRUST the Race Week structure but maybe ensure it doesn't EXCEED baseline?
             curr_actual_vol = get_week_volume(week)
             if curr_actual_vol > current_baseline_vol:
                 print(f"[Week {i+1} {week.weekStarting}] RACE: Cap applied (was {curr_actual_vol/1000:.1f}k)")
                 set_week_volume(week, current_baseline_vol)
             else:
                 print(f"[Week {i+1} {week.weekStarting}] RACE: Keeping {curr_actual_vol/1000:.1f}k")
             
             # Do not update baseline
             
             
        elif status == "marathon":
             # Marathon week - usually very low volume before + 42k
             # Leave as is
             print(f"[Week {i+1} {week.weekStarting}] MARATHON: Touching nothing.")
     
    
    save_plan(weeks, plan_path)

if __name__ == "__main__":
    recalculate_plan()
