import sys
import os
import json
from sqlmodel import Session, select

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.core.database import engine, RunnerPlan
from app.core.mappers import plan_to_relational

def main():
    print("Migrating plans to relational tables...")
    
    with Session(engine) as session:
        # fetch all plans
        plans = session.exec(select(RunnerPlan)).all()
        
        print(f"Found {len(plans)} plans.")
        
        for plan in plans:
            print(f"Processing Plan ID {plan.id}: {plan.title} (Active: {plan.is_active})")
            
            try:
                plan_data = json.loads(plan.plan_json)
                
                # Check if already populated? 
                # plan_to_relational handles clearing existing data, so it's safe to re-run.
                
                plan_to_relational(session, plan, plan_data)
                print(f"  -> Successfully migrated to relational schema.")
                
            except Exception as e:
                print(f"  -> Failed to migrate plan {plan.id}: {e}")
                
    print("Migration complete.")

if __name__ == "__main__":
    main()
