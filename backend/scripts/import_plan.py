import json
import os
import sys
import argparse

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.core.database import engine
from sqlmodel import Session
from app.core.services import save_plan_to_db

def main():
    parser = argparse.ArgumentParser(description="Import a plan JSON file into the database.")
    parser.add_argument("filepath", nargs="?", default="data/plan.json", help="Path to the plan JSON file (default: data/plan.json)")
    parser.add_argument("--user", default="mike", help="Username to assign plan to (default: mike)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.filepath):
        print(f"Error: File '{args.filepath}' not found.")
        sys.exit(1)
        
    print(f"Reading plan from {args.filepath}...")
    try:
        with open(args.filepath, 'r') as f:
            plan_data = json.load(f)
            
        if not isinstance(plan_data, list):
             print("Error: Plan JSON must be a list of weeks.")
             sys.exit(1)
             
        print(f"Importing plan with {len(plan_data)} weeks for user '{args.user}'...")
        
        with Session(engine) as session:
            saved_plan = save_plan_to_db(plan_data, session, username=args.user)
            print(f"Success! Plan saved with ID {saved_plan.id} and title '{saved_plan.title}'.")
        
    except json.JSONDecodeError:
        print(f"Error: '{args.filepath}' is not valid JSON.")
        sys.exit(1)
    except Exception as e:
        print(f"Error importing plan: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
