from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import os
from contextlib import asynccontextmanager

from app.core.database import create_db_and_tables, engine, User, RunnerPlan
from app.routers import pages, api

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # Create a default user and plan if none exist (for local dev transition)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "mike")).first()
        if not user:
            print("Creating default user 'mike'...")
            user = User(username="mike", email="mike@example.com")
            session.add(user)
            session.commit()
            session.refresh(user)
            
            # Import existing plan.json into DB for this user
            if os.path.exists("data/plan.json"):
                print("Importing local plan.json to DB...")
                with open("data/plan.json", "r") as f:
                    plan_data = f.read()
                
                plan = RunnerPlan(title="Bunbury 2026", plan_json=plan_data, user_id=user.id, is_active=True)
                session.add(plan)
                session.commit()
                
    yield

app = FastAPI(lifespan=lifespan)

app.include_router(pages.router)
app.include_router(api.router)

# serve root files as fallback if needed or specific static dir
# app.mount("/static", StaticFiles(directory="app/static"), name="static")
