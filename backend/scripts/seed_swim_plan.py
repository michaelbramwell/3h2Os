import sys
import os
from datetime import date, timedelta

# Add parent dir to sys.path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import RunnerPlan, PlanWeek, PlanWorkout, engine, User
from sqlmodel import Session, select
from app.models.domain import ActivityType, PlanType


def create_swimming_plan():
    # Use context manager for session
    with Session(engine) as db:
        # 0. Find the user 'mike' (or default user)
        user = db.exec(select(User).where(User.username == "mike")).first()
        if not user:
            print("User 'mike' not found. Checking for any user...")
            user = db.exec(select(User)).first()
            if not user:
                print("No users found in database. Please create a user first.")
                return

        print(f"Creating plan for User: {user.username} (ID: {user.id})")

        # 1. Create the Plan
        plan = RunnerPlan(
            title="Rottnest Channel Swim 2025-26",
            type="swimming",  # PlanType.SWIMMING
            is_active=True,
            user_id=user.id,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        print(f"Created Plan: {plan.title} (ID: {plan.id})")

        # Define the schedule data based on the Excel analysis
        # Using the key weeks identified, we will interpolate or fill the gaps.
        schedule = [
            {
                "week": 1,
                "start_date": date(2025, 10, 5),
                "target_km": 9.0,
                "phase": "Speed/Sprints (Pool)",
                "notes": "Focus: Race Preparation & Nutrition. Build up strength and speed by doing lots of sprint work.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Pool Intervals",
                        "desc": "Intervals at the pool. Focus on speed.",
                        "dist": 3000,
                    },
                    {
                        "day": 3,
                        "name": "Drills & Skills",
                        "desc": "2.3km drills focus. Technical work.",
                        "dist": 2300,
                    },
                    {
                        "day": 5,
                        "name": "Long Swim",
                        "desc": "Saturday long swim. Build endurance.",
                        "dist": 3700,
                    },
                ],
            },
            {
                "week": 4,
                "start_date": date(2025, 10, 26),
                "target_km": 7.0,
                "phase": "Recovery",
                "notes": "Recovery Week. Allow adaptation.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Easy Swim",
                        "desc": "Easy recovery swim.",
                        "dist": 2500,
                    },
                    {
                        "day": 3,
                        "name": "Technique",
                        "desc": "Focus on form, low intensity.",
                        "dist": 2000,
                    },
                    {
                        "day": 5,
                        "name": "Short Aerobic",
                        "desc": "Keep it aerobic and relaxed.",
                        "dist": 2500,
                    },
                ],
            },
            {
                "week": 5,
                "start_date": date(2025, 11, 2),
                "target_km": 10.0,
                "phase": "Form/Open Water Technique",
                "notes": "Stretch & count strokes, aim to lengthen stroke. Lots of arm drills/single-arm/drags etc.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Technique Focus",
                        "desc": "Count strokes, lengthen stroke.",
                        "dist": 3000,
                    },
                    {
                        "day": 3,
                        "name": "Drills",
                        "desc": "Arm drills, single-arm, drags.",
                        "dist": 3000,
                    },
                    {
                        "day": 5,
                        "name": "Endurance",
                        "desc": "Aerobic maintenance.",
                        "dist": 4000,
                    },
                ],
            },
            {
                "week": 9,
                "start_date": date(2025, 11, 30),
                "target_km": 15.4,
                "phase": "Speed/Thresholds (Ocean)",
                "notes": "Hold faster pace longer, aim for reduced CJJ times. Start practice feeding. Switch to ocean.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Pool Speed",
                        "desc": "Last pool session of the week. High intensity.",
                        "dist": 3500,
                    },
                    {
                        "day": 3,
                        "name": "Ocean Threshold",
                        "desc": "Fence swims with feeding practice.",
                        "dist": 4000,
                    },
                    {
                        "day": 5,
                        "name": "Rehearsal Swim",
                        "desc": "10km Rehearsal swim if scheduled, else long ocean swim.",
                        "dist": 7900,
                    },
                ],
            },
            {
                "week": 13,
                "start_date": date(2025, 12, 28),
                "target_km": 15.4,
                "phase": "Endurance/Distance (Ocean)",
                "notes": "Longer distance swims, to fence & back. Test sea sickness tablets. Establish food/drink routine.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Distance Reps",
                        "desc": "Longer reps in ocean/pool.",
                        "dist": 4000,
                    },
                    {
                        "day": 3,
                        "name": "River Swim",
                        "desc": "7.5km River swim with paddler (if scheduled).",
                        "dist": 7500,
                    },
                    {
                        "day": 5,
                        "name": "Back-to-Back",
                        "desc": "Fatigue resistance training.",
                        "dist": 3900,
                    },
                ],
            },
            {
                "week": 17,
                "start_date": date(2026, 1, 25),
                "target_km": 21.6,
                "phase": "Distance/Hold Pace (Ocean)",
                "notes": "Min 10km Coogee to South Beach swim with paddler. Boat practice.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Pace Hold",
                        "desc": "Hold race pace for duration.",
                        "dist": 5000,
                    },
                    {
                        "day": 3,
                        "name": "Ocean Long",
                        "desc": "Coogee to South Beach (10km) or equivalent.",
                        "dist": 10000,
                    },
                    {
                        "day": 5,
                        "name": "Recovery/Support",
                        "desc": "Support swim or recovery.",
                        "dist": 6600,
                    },
                ],
            },
            {
                "week": 20,
                "start_date": date(2026, 2, 15),
                "target_km": 13.7,
                "phase": "Taper 1/2",
                "notes": "Begin reducing volume. Maintain some intensity.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Taper Swim 1",
                        "desc": "Reduced volume, keep intensity.",
                        "dist": 4000,
                    },
                    {
                        "day": 3,
                        "name": "Taper Swim 2",
                        "desc": "Short intervals.",
                        "dist": 3000,
                    },
                    {
                        "day": 5,
                        "name": "Taper Long",
                        "desc": "Reduced long swim.",
                        "dist": 6700,
                    },
                ],
            },
            {
                "week": 21,
                "start_date": date(2026, 2, 22),
                "target_km": 9.0,
                "phase": "Taper",
                "notes": "Final Taper week. Race Prep.",
                "workouts": [
                    {
                        "day": 1,
                        "name": "Final Sharpening",
                        "desc": "Short sprints, lots of rest.",
                        "dist": 3000,
                    },
                    {
                        "day": 3,
                        "name": "Shakeout",
                        "desc": "Easy swimming.",
                        "dist": 2000,
                    },
                    {
                        "day": 5,
                        "name": "Pre-Race",
                        "desc": "Very short, feel the water.",
                        "dist": 4000,
                    },
                ],
            },
        ]

        # Interpolation Logic
        current_plan_date = schedule[0]["start_date"]
        # Extend until the end of the last defined week
        end_date = schedule[-1]["start_date"] + timedelta(days=7)

        key_weeks = {s["start_date"]: s for s in schedule}

        week_cursor = current_plan_date
        week_count = 1

        while week_cursor < end_date:
            # Check if this specific date is a key week
            week_data = key_weeks.get(week_cursor)

            # If not a key week, default to the previous key week's phase/structure
            if not week_data:
                potential_weeks = [s for s in schedule if s["start_date"] < week_cursor]
                if potential_weeks:
                    base_week = potential_weeks[-1]
                    week_data = {
                        "phase": base_week["phase"],
                        "notes": base_week["notes"],
                        "workouts": base_week["workouts"],
                    }
                else:
                    week_data = {"phase": "Base", "notes": "", "workouts": []}

            # Create the Week
            plan_week = PlanWeek(
                start_date=week_cursor, status="normal", plan_id=plan.id
            )
            db.add(plan_week)
            db.commit()
            db.refresh(plan_week)

            # Create Workouts for this week
            workouts_def = week_data.get("workouts", [])

            for w in workouts_def:
                # Calculate actual date: start_date + day_offset
                w_date = week_cursor + timedelta(days=w["day"])
                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_name = day_names[w["day"]]

                workout = PlanWorkout(
                    week_id=plan_week.id,
                    date=w_date,
                    day_name=day_name,
                    name=w["name"],
                    description=f"{week_data.get('notes', '')}\n\n{w['desc']}",
                    activity_type="Swimming",
                    distance_m=w["dist"],
                )
                db.add(workout)

            db.commit()
            print(
                f"Created Week {week_count} ({week_cursor}): {len(workouts_def)} workouts - {week_data['phase']}"
            )

            week_cursor += timedelta(days=7)
            week_count += 1

        print("Swimming Plan Import Complete.")


if __name__ == "__main__":
    create_swimming_plan()
