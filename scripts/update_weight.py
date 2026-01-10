import json
import sys
import subprocess
from datetime import datetime, timedelta, timezone

def get_awst_today():
    """Returns today's date string in AWST (UTC+8)."""
    awst_now = datetime.now(timezone.utc) + timedelta(hours=8)
    return awst_now.strftime("%Y-%m-%d")

def update_weight(new_weight: float):
    file_path = "data/context.json"
    
    try:
        with open(file_path, "r") as f:
            context = json.load(f)
        
        today = get_awst_today()
        
        # Update current weight
        context["runner"]["weight_kg"]["current"] = new_weight
        
        # Add to history
        history = context["runner"]["weight_kg"].get("history", [])
        # Check if we already have an entry for today
        existing = next((item for item in history if item["date"] == today), None)
        if existing:
            existing["weight"] = new_weight
        else:
            history.append({"date": today, "weight": new_weight})
        
        context["runner"]["weight_kg"]["history"] = history
        
        # Update status
        context["status"]["lastUpdated"] = today
        
        with open(file_path, "w") as f:
            json.dump(context, f, indent=2)
        
        print(f"Successfully updated weight to {new_weight}kg (AWST) in context.json")
        
        # Regenerate Markdown files
        print("Regenerating Markdown files...")
        subprocess.run(["python3", "generate_plan_md.py"], check=True)
        
    except Exception as e:
        print(f"Error updating weight: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 update_weight.py <weight_in_kg>")
        sys.exit(1)
    
    try:
        weight = float(sys.argv[1])
        update_weight(weight)
    except ValueError:
        print("Error: Weight must be a number.")
        sys.exit(1)
