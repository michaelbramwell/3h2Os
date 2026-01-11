import json
import os
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.domain import Week, Day, Workout, load_plan, load_actuals

def format_zones(zones, type_str):
    """Formats zone data into a readable string for the fridge."""
    active_zones = [z for z in zones if z.get("secsInZone", 0) > 30]
    if not active_zones:
        return ""
    
    parts = []
    for z in active_zones:
        zn = z["zoneNumber"]
        sec = z["secsInZone"]
        mins = int(sec // 60)
        rem = int(sec % 60)
        time_str = f"{mins}m {rem}s" if mins > 0 else f"{rem}s"
        
        avg = z.get("avgValue", 0)
        if type_str == "pace" and avg > 0:
            p_min = int(16.6666666667 / avg)
            p_sec = int((1000 / avg) % 60)
            parts.append(f"Z{zn} ({p_min}:{p_sec:02d} @ {time_str})")
        elif type_str == "hr" and avg > 0:
            parts.append(f"Z{zn} ({avg:.0f}bpm @ {time_str})")
        elif type_str == "power" and avg > 0:
            parts.append(f"Z{zn} ({avg:.0f}W @ {time_str})")
    return " | ".join(parts)

def generate_fridge_sheets():
    # Create fridge directory if it doesn't exist
    if not os.path.exists("fridge"):
        os.makedirs("fridge")
        print("Created fridge/ directory.")

    # Load sources
    plan_data = load_plan("data/plan.json")
    actuals_data = load_actuals("data/actuals.json")

    actuals_by_date = {}
    for act in actuals_data:
        if act.date not in actuals_by_date:
            actuals_by_date[act.date] = []
        actuals_by_date[act.date].append(act)

    for i, week in enumerate(plan_data):
        week_num = i + 1
        week_start = week.weekStarting
        date_obj = datetime.strptime(week_start, "%Y-%m-%d")
        formatted_start = date_obj.strftime("%B %d, %Y")
        
        filename = f"fridge/Week_{week_num:02d}.md"
        
        md = []
        md.append(f"# WEEK {week_num} | FRIDGE SHEET")
        md.append(f"**Starting {formatted_start}**")
        md.append("")
        md.append("---")
        md.append("")
        
        for day_name in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            day_data = week.days[day_name]
            workouts = day_data.workouts
            day_date = day_data.date
            day_label = datetime.strptime(day_date, "%Y-%m-%d").strftime("%b %d")
            
            md.append(f"## {day_name.upper()} ({day_label})")
            
            # Show actuals first if they exist
            day_actuals = actuals_by_date.get(day_date, [])
            if day_actuals:
                for act in day_actuals:
                    km = act.distance_m / 1000
                    metrics = []
                    if act.average_hr: metrics.append(f"{act.average_hr:.0f}bpm")
                    if act.average_power: metrics.append(f"{act.average_power:.0f}W")
                    telemetry = f" ({', '.join(metrics)})" if metrics else ""
                    
                    md.append(f"- [x] **ACTUAL: {km:.2f}km**{telemetry} ✓")
            
            if not workouts:
                if not day_actuals:
                    md.append("- [ ] **REST DAY**")
            else:
                for w in workouts:
                    # Check if this workout was likely matched (very basic check)
                    was_done = False
                    if day_actuals:
                        was_done = True # Assume if any run happened on that day, the workout was attempted
                    
                    status = "[x]" if was_done else "[ ]"
                    time_label = f"[{w.timeOfDay}] " if w.timeOfDay else ""
                    md.append(f"- {status} **{time_label}{w.name}** ({w.type})")
            
            md.append("")

        md.append("---")
        md.append("### GUIDELINES")
        md.append("- **Paces:** Easy (5:45-6:15) | Steady (5:10-5:20) | MP (5:30-5:40) | Threshold (4:40-4:50)")
        md.append("- **90/900 Rule:** 90g Carbs + 900mg Sodium per hour on Long Runs.")
        md.append("- **Weight Goal:** Maintain mechanical load resilience (current vs target).")
        md.append("")
        md.append("### NOTES / VITALS")
        md.append("- Weight: _______ kg")
        md.append("- Sleep: _______ hrs")
        md.append("- Fatigue (1-10): _______")
        md.append("")

        with open(filename, "w") as f:
            f.write("\n".join(md))
            
    print(f"Successfully generated {len(plan_data)} fridge sheets in fridge/")

if __name__ == "__main__":
    generate_fridge_sheets()
