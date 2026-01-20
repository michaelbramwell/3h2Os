from sqlmodel import Session, select
import json
import os
import sys

# Ensure backend acts as root
sys.path.append(os.getcwd())

from app.core.database import engine, User, RunnerProfile
from app.schemas import TrainingZones, TrainingZone

def populate_zones():
    with Session(engine) as session:
        # Get default user
        username = os.environ.get("DEFAULT_USERNAME", "runner")
        user = session.exec(select(User).where(User.username == username)).first()
        
        if not user or not user.profile:
            print("User/Profile not found")
            return

        print(f"Checking zones for {username}...")
        
        if user.profile.training_zones_json:
            print("Zones already exist:")
            print(user.profile.training_zones_json[:100] + "...")
            # Optional: Overwrite if you want to force it
            # return 

        # Create 3h20 Marathon Paces
        # Goal: Sub 3:20 (say 3:19) -> 4:43 min/km
        # But wait, user said Sub-4 in screenshot. 
        # Let's derive roughly from Sub-4 for now to be safe (5:41/km), 
        # but user might want 3h20 based on repo name? 
        # The screenshot shows "Sub-4 Marathon". I'll stick to that.
        
        # Sub 4:00 = 5:41 min/km = 2.93 m/s
        # Z1: Recovery > 6:30 (avg 2.56 m/s)
        # Z2: Easy 5:50 - 6:30 (2.56 - 2.85 m/s)
        # Z3: Tempo 5:15 - 5:45 (2.90 - 3.17 m/s) <-- Marathon Pace in here
        # Z4: Threshold 4:50 - 5:10 (3.22 - 3.45 m/s)
        # Z5: VO2 < 4:45 (> 3.5 m/s)

        # Let's define pace zones in m/s (Lower bound of the zone)
        # Note: Logic in UI: 
        # Range = NextZone.start - currentZone.start
        
        # Low Speed (m/s) corresponds to SLOWEST pace (High min/km)
        # Wait, usually zones are defined by the Start (min val).
        # For Speed: Start = Slowest speed.
        # Z1 Start: 0.0
        # Z2 Start: 2.5 m/s (6:40/km)
        # Z3 Start: 2.8 m/s (5:57/km)
        # Z4 Start: 3.2 m/s (5:12/km)
        # Z5 Start: 3.5 m/s (4:45/km)
        # Z6 Start: 3.9 m/s (4:16/km)
        
        pace_zones = [
            TrainingZone(zone=1, lowBoundary_m_s=0.0, description="Recovery. Very easy jogging."),
            TrainingZone(zone=2, lowBoundary_m_s=2.5, description="Easy. Conversational pace."),
            TrainingZone(zone=3, lowBoundary_m_s=2.9, description="Tempo. Marathon effort."),
            TrainingZone(zone=4, lowBoundary_m_s=3.3, description="Threshold. Comfortably hard."),
            TrainingZone(zone=5, lowBoundary_m_s=3.6, description="VO2 Max. Hard effort."),
            TrainingZone(zone=6, lowBoundary_m_s=4.0, description="Anaerobic. Sprints.")
        ]
        
        zones_obj = TrainingZones(pace=pace_zones)
        zones_json = zones_obj.model_dump_json()
        
        user.profile.training_zones_json = zones_json
        session.add(user.profile)
        session.commit()
        print("Zones populated successfully.")

if __name__ == "__main__":
    populate_zones()
