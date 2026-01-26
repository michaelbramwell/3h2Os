from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
load_dotenv(find_dotenv())

from app.core.database import create_db_and_tables, engine, User, RunnerPlan
from app.routers import pages, api
from app.core.migrations_logic import migrate_context_json
from app.core.auth import verify_jwt_middleware


# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables() # Disabled in favor of Alembic migrations
    # Create a default user and plan if none exist (for local dev transition)
    # Note: This logic might fail if tables don't exist yet (i.e. if migration hasn't run)

    try:
        with Session(engine) as session:
            default_username = os.environ.get("DEFAULT_USERNAME", "runner")
            user = session.exec(
                select(User).where(User.username == default_username)
            ).first()
            if not user:
                # TODO: Transition this to Keycloak user sync or removal
                print(f"Creating default user '{default_username}'...")
                user = User(
                    username=default_username, email=f"{default_username}@example.com"
                )
                session.add(user)
                session.commit()
                session.refresh(user)

                # Import existing plan.json into DB for this user
                if os.path.exists("data/plan.json"):
                    print("Importing local plan.json to DB...")
                    with open("data/plan.json", "r") as f:
                        plan_data = f.read()

                    plan = RunnerPlan(
                        title="Bunbury 2026",
                        plan_json=plan_data,
                        user_id=user.id,
                        is_active=True,
                    )
                    session.add(plan)
                    session.commit()

            # Run Context Migration
            migrate_context_json(session)

    except Exception as e:
        print(f"Startup data init skipped (tables likely missing): {e}")

    yield


# Apply global auth middleware
app = FastAPI(lifespan=lifespan, dependencies=[Depends(verify_jwt_middleware)])

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://3h2os.com",
    "https://auth.3h2os.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pages.router)
app.include_router(api.router, prefix="/api")

# serve root files as fallback if needed or specific static dir
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Force reload triggers
