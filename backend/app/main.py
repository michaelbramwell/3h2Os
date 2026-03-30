import asyncio
import logging

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
from app.core.auth import verify_jwt_middleware
from db.migrate import migrate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Background: daily profile sync
# ---------------------------------------------------------------------------

_PROFILE_SYNC_INTERVAL_SECS = int(
    os.environ.get("PROFILE_SYNC_INTERVAL_SECS", 86400)  # 24 hours
)


async def _daily_profile_sync_loop() -> None:
    """
    Asyncio background task: runs every PROFILE_SYNC_INTERVAL_SECS seconds.
    Iterates all users with a connected Strava token and re-syncs their profile.
    Garmin profile re-sync happens on each manual Garmin activity sync (sync.py),
    since Garmin tokens are session-scoped and not persisted server-side.
    """
    while True:
        await asyncio.sleep(_PROFILE_SYNC_INTERVAL_SECS)
        logger.info("Daily profile sync: starting background pass")
        try:
            with Session(engine) as session:
                from sqlmodel import select as _select
                from app.core.database import StravaToken
                from app.services.strava import StravaService

                strava_tokens = session.exec(_select(StravaToken)).all()
                for token in strava_tokens:
                    try:
                        svc = StravaService(session)
                        refreshed = svc.refresh_if_needed(token)
                        svc.merge_athlete_profile(token.user_id, refreshed.access_token)
                        logger.debug(
                            f"Background Strava profile sync done for user {token.user_id}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Background Strava profile sync failed for user {token.user_id}: {e}"
                        )

        except Exception as e:
            logger.error(f"Daily profile sync loop error: {e}")


# --- Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate(engine)

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

    except Exception as e:
        print(f"Startup data init skipped (tables likely missing): {e}")

    # Start the daily profile sync background task
    sync_task = asyncio.create_task(_daily_profile_sync_loop())

    yield

    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass


# Apply global auth middleware
app = FastAPI(lifespan=lifespan, dependencies=[Depends(verify_jwt_middleware)])

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Add production domains from environment variables if present
if cors_env := os.environ.get("CORS_ORIGINS"):
    for o in cors_env.split(","):
        o = o.strip()
        if o.startswith("http://") or o.startswith("https://"):
            origins.append(o)
        else:
            pass

if domain := os.environ.get("DOMAIN"):
    origins.append(f"https://{domain}")
    origins.append(f"https://auth.{domain}")
    origins.append(f"https://www.{domain}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api")
app.include_router(
    api.router
)  # Mount at root as well to handle proxy stripping behavior
app.include_router(pages.router)

# serve root files as fallback if needed or specific static dir
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Force reload triggers
