import json
import os
from datetime import datetime

def generate_fridge_sheets():
    # Create fridge directory if it doesn't exist
    if not os.path.exists("fridge"):
        os.makedirs("fridge")
        print("Created fridge/ directory.")

    # Load plan
    with open("plan.json", "r") as f:
        plan_data = json.load(f)

    for i, week in enumerate(plan_data):
        week_num = i + 1
        week_start = week["weekStarting"]
        date_obj = datetime.strptime(week_start, "%Y-%m-%d")
        formatted_start = date_obj.strftime("%B %d, %Y")
        
        filename = f"fridge/Week_{week_num:02d}.md"
        
        md = []
        md.append(f"# WEEK {week_num} | FRIDGE SHEET")
        md.append(f"**Starting {formatted_start}**")
        md.append("")
        md.append("---")
        md.append("")
        
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            day_data = week["days"][day]
            workouts = day_data["workouts"]
            day_date = datetime.strptime(day_data["date"], "%Y-%m-%d").strftime("%b %d")
            
            md.append(f"## {day.upper()} ({day_date})")
            
            if not workouts:
                md.append("- [ ] **REST DAY**")
            else:
                for w in workouts:
                    time_label = f"[{w['timeOfDay']}] " if 'timeOfDay' in w else ""
                    md.append(f"- [ ] **{time_label}{w['name']}** ({w['type']})")
            
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
