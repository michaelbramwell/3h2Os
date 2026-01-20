import sys
import os
import json
from sqlmodel import Session, select

# Add backend to path
sys.path.append(os.getcwd())

from app.core.database import engine, User, RunnerProfile, RunnerProject

def populate():
    with Session(engine) as session:
        # Try finding 'mike'
        user = session.exec(select(User).where(User.username == "mike")).first()
        
        if not user:
            print("Creating user 'mike'")
            user = User(username="mike", email="mike@example.com")
            session.add(user)
            session.commit()
            session.refresh(user)
            
        if not user.profile:
            print("Creating profile for 'mike'")
            profile = RunnerProfile(
                user_id=user.id,
                age=30,
                gender="M",
                height_cm=180,
                current_weight=75.0,
                target_weight=70.0,
                training_zones_json="{}",
                fueling_json="{}"
            )
            session.add(profile)
            session.commit()
            session.refresh(user)
from datetime import date
            
        if not user.project:
            print("Creating project for 'mike'")
            project = RunnerProject(
                user_id=user.id,
                name="3h2Os Attempt",
                goal="Sub 3:20 Marathon",
                event="Perth Marathon",
                event_date=date(2026, 10, 10)
            )
            session.add(project)
            session.commit()
            session.refresh(user)

        print(f"Updating profile for user: {user.username}")

        # Defaults for ~3h20m marathoner (approx 4:44/km MP)
        # Values in m/s
        # Z1: < 2.77 (Slower than 6:00/km)
        # Z2: 2.77 - 3.17 (6:00 - 5:15/km)
        # Z3: 3.17 - 3.70 (5:15 - 4:30/km)
        # Z4: 3.70 - 4.16 (4:30 - 4:00/km)
        # Z5: > 4.16 (Faster than 4:00/km)
        
        pace_zones = [
            {"zone": 1, "lowBoundary_m_s": 0.0, "description": "Recovery"},
            {"zone": 2, "lowBoundary_m_s": 2.77, "description": "Easy"},
            {"zone": 3, "lowBoundary_m_s": 3.17, "description": "Tempo/Steady"},
            {"zone": 4, "lowBoundary_m_s": 3.70, "description": "Threshold"},
            {"zone": 5, "lowBoundary_m_s": 4.16, "description": "VO2 Max"}
        ]
        
        fueling = {
            "carbsPerHr": 60,
            "sodiumPerHr": 500,
            "preRunCarbs": 50
        }
        
        training_zones = {
            "pace": pace_zones,
            "heartRate": [] 
        }
        
        user.profile.training_zones_json = json.dumps(training_zones)
        user.profile.fueling_json = json.dumps(fueling)
        
        session.add(user.profile)
        session.commit()
        print("Updated profile with zones and fueling")

if __name__ == "__main__":
    populate()
