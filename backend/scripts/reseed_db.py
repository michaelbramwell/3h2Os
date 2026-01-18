import json
import os
import sys
from sqlmodel import Session, select
from typing import List, Dict

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, ActualActivity, User
from app.schemas import ActivitySchema, HrZone
from app.services.activities import ActivityService

def reseed():
    print("Reseeding activities from data/actuals.json...")
    
    if not os.path.exists("data/actuals.json"):
        print("data/actuals.json not found.")
        return

    with open("data/actuals.json", "r") as f:
        raw_data = json.load(f)

    # Convert raw dicts to ActivitySchema
    schemas = []
    for item in raw_data:
        try:
            # Pydantic will automap zoneLowBoundary -> zoneLow if aliases set up right
            schema = ActivitySchema(**item)
            schemas.append(schema)
        except Exception as e:
            # print(f"Skipping activity {item.get('date', '?')}: {e}")
            pass

    print(f"Parsed {len(schemas)} valid activities from {len(raw_data)} records.")

    with Session(engine) as session:
        service = ActivityService(session)
        
        # Ensure user exists
        user = session.exec(select(User).where(User.username == "mike")).first()
        if not user:
            print("Creating default user 'mike'")
            user = User(username="mike", email="mike@example.com")
            session.add(user)
            session.commit()
            
        count = service.save_activities(schemas, username="mike")
        print(f"Saved/Updated {count} activities.")

if __name__ == "__main__":
    reseed()
