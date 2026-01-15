from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import os
from contextlib import asynccontextmanager

from app.core.database import create_db_and_tables, engine, User, RunnerPlan
from app.routers import pages, api
from app.core.migrations_logic import migrate_context_json

# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables() # Disabled in favor of Alembic migrations
    # Create a default user and plan if none exist (for local dev transition)
    # Note: This logic might fail if tables don't exist yet (i.e. if migration hasn't run)

    try:
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
            
            # Run Context Migration
            migrate_context_json(session)
            
    except Exception as e:
        print(f"Startup data init skipped (tables likely missing): {e}")
                
    yield

app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pages.router)
app.include_router(api.router)

# serve root files as fallback if needed or specific static dir
app.mount("/static", StaticFiles(directory="app/static"), name="static")
