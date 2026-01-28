from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
import os
from typing import List

from app.core.database import get_session, User
from app.core.auth import verify_jwt_middleware
from app.services.plans import PlanService
from app.services.context import ContextService
from app.services.activities import ActivityService
from app.services.garmin import GarminService
from app.core.validation import ValidationWarningError
from dataclasses import asdict
from app.schemas import (
    WeekSchema,
    PlanUpdateResponse,
    ContextSchema,
    ActivitySchema,
    PlanCreate,
    WorkoutUpdate,
    WorkoutCreate,
    GarminLogin,
    GarminToken,
)
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta

# Setup logger for API routes
logger = logging.getLogger("app.api")

router = APIRouter()


# --- Dependency Injection Functions ---
def get_plan_service(session: Session = Depends(get_session)) -> PlanService:
    return PlanService(session)


def get_context_service(session: Session = Depends(get_session)) -> ContextService:
    return ContextService(session)


def get_activity_service(session: Session = Depends(get_session)) -> ActivityService:
    return ActivityService(session)


def get_garmin_service(session: Session = Depends(get_session)) -> GarminService:
    return GarminService(session)


async def get_current_user(
    request: Request, session: Session = Depends(get_session)
) -> User:
    # 1. Get Payload from verify_jwt_middleware
    user_payload = getattr(request.state, "user", None)

    username = "runner"  # Default fallback
    email = "runner@example.com"

    if user_payload:
        # Keycloak usually sends 'preferred_username'
        username = user_payload.get(
            "preferred_username", user_payload.get("sub", "runner")
        )
        email = user_payload.get("email", f"{username}@example.com")
        logger.info(f"User resolved from JWT: {username}")
    else:
        # Fallback to Env if set (for local dev without auth header)
        if os.environ.get("DEFAULT_USERNAME"):
            username = os.environ.get("DEFAULT_USERNAME")
            logger.info(f"User resolved from DEFAULT_USERNAME env: {username}")
        else:
            logger.info(f"User defaulted to hardcoded fallback: {username}")

    # 2. Find or Create User in DB
    user = session.exec(select(User).where(User.username == username)).first()
    if not user:
        logger.info(f"User {username} not found in DB. Auto-provisioning new user.")
        # Auto-provision (JIT)
        user = User(username=username, email=email)
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        logger.info(f"User {username} found in DB with ID: {user.id}")

    return user


class WeightUpdate(BaseModel):
    weight: float


# --- Routes ---


@router.post("/context/weight")
async def update_weight(
    update: WeightUpdate,
    service: ContextService = Depends(get_context_service),
    user: User = Depends(get_current_user),
):
    """
    Update the runner's weight (Current & History).
    """
    try:
        new_weight = service.update_weight(update.weight, user=user)
        return {"status": "success", "current_weight": new_weight}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actuals")
async def save_actuals(
    activities: List[ActivitySchema],
    service: ActivityService = Depends(get_activity_service),
    user: User = Depends(get_current_user),
):
    """
    Bulk save/update actual activities.
    """
    try:
        count = service.save_activities(activities, user=user)
        return {"status": "success", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans", response_model=PlanUpdateResponse)
async def create_plan(
    plan_create: PlanCreate,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Create a new plan. It is created as inactive by default.
    """
    try:
        plan_dicts = [w.model_dump() for w in plan_create.weeks]
        new_plan = service.create_or_update_plan(
            plan_dicts,
            user=user,
            title=plan_create.title,
            plan_type=plan_create.type,
            activate=False,
        )
        return {
            "status": "success",
            "message": "Plan created",
            "id": new_plan.id,
            "title": new_plan.title,
            "type": new_plan.type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class PlanMeta(BaseModel):
    id: int
    title: str
    type: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/plans", response_model=List[PlanMeta])
async def get_plans(
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Get all plans for the current user.
    """
    try:
        plans = service.get_plans(user)
        return plans
    except Exception as e:
        logger.error(f"Error getting plans: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}/activate")
async def set_active_plan(
    plan_id: int, service: PlanService = Depends(get_plan_service)
):
    """
    Mark a specific plan as active.
    """
    try:
        activated = service.activate_plan(plan_id)
        return {
            "status": "success",
            "message": f"Plan {plan_id} activated",
            "id": activated.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Delete a specific plan.
    """
    try:
        service.delete_plan(plan_id, user)
        return {"status": "success", "message": f"Plan {plan_id} deleted"}
    except ValueError as e:
        # If the service raises a ValueError, check if it's "not found" vs "permission denied"
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def update_plan(
    plan_data: List[WeekSchema],
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Update the active plan for the default user.
    Archives current and creates a new ACTIVE plan version.
    """
    try:
        plan_dicts = [w.model_dump() for w in plan_data]
        new_plan = service.create_or_update_plan(plan_dicts, user=user, activate=True)
        return {
            "status": "success",
            "message": "Plan updated",
            "id": new_plan.id,
            "title": new_plan.title,
            "type": new_plan.type,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plan.json", response_model=List[WeekSchema])
async def get_plan(
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Get the currently active plan as a list of Weeks.
    """
    return service.get_active_plan(user=user)


@router.get("/context.json", response_model=ContextSchema)
async def get_context(
    service: ContextService = Depends(get_context_service),
    user: User = Depends(get_current_user),
):
    """
    Get the context data
    """
    return service.get_context(user=user)


@router.get("/actuals.json", response_model=List[ActivitySchema])
async def get_actuals(
    service: ActivityService = Depends(get_activity_service),
    plan_service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Get the actual activities from the database, filtered by the active plan type.
    """
    # 1. Determine active plan type
    # We need to import RunnerPlan since we're using it in a select statement
    from app.core.database import RunnerPlan

    # Let's get the Active Plan Type
    stmt = (
        select(RunnerPlan)
        .where(RunnerPlan.user_id == user.id)
        .where(RunnerPlan.is_active == True)
    )
    active_plan = service.session.exec(stmt).first()

    filter_types = None
    if active_plan:
        if active_plan.type == "swimming":
            filter_types = [
                "swimming",
                "swim",
                "pool",
                "lap_swimming",
                "open_water_swimming",
            ]
        elif active_plan.type == "running":
            filter_types = ["running", "run", "trail_running", "treadmill_running"]

    return service.get_activities(user=user, filter_types=filter_types)


@router.post("/integrations/garmin/sync")
async def sync_garmin_activities(
    request: Request,
    days: int = 7,
    # Remove injection here, construct manually with header
    # garmin_service: GarminService = Depends(get_garmin_service),
    activity_service: ActivityService = Depends(get_activity_service),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Syncs activities from Garmin Connect for the specified number of past days.
    Requires X-Garmin-Token header.
    """
    token = request.headers.get("X-Garmin-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing Garmin Token in headers")

    try:
        # Initialize service with token from header using context manager
        with GarminService(session, token_b64=token) as garmin_service:
            if not garmin_service.client:
                raise HTTPException(
                    status_code=401, detail="Garmin token invalid or expired"
                )

            # Use simple server time, defaulting to last N days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            activities = garmin_service.fetch_activities(
                start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
            )

            # Convert dataclasses to Pydantic models
            schema_activities = [ActivitySchema(**asdict(a)) for a in activities]

            count = activity_service.save_activities(schema_activities, user=user)

            # Trigger plan recalculation based on new actuals
            try:
                # Instantiate PlanService (using existing session/user)
                # Note: We rely on the fact that 'session' is still open.
                plan_service = PlanService(session)
                plan_service.recalculate_plan_progression(user)
                logger.info(f"Triggered plan recalculation for user {user.username}")
            except Exception as pe:
                logger.error(f"Plan recalculation failed after sync: {pe}")
                # We don't fail the sync request itself, just log the error

            return {
                "status": "success",
                "count": count,
                "message": f"Synced {count} activities.",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        # Return 500 but with JSON detail
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.get("/context/markdown")
async def get_context_markdown():
    """
    Deprecated: Context is now database-driven.
    """
    return {"content": ""}


# TODO: Add authentication/authorization checks for all mutation endpoints
# (create/update/delete workouts, plans, etc.) to prevent unauthorized access.
# Currently relies on default username from environment.


@router.post("/workouts")
async def create_workout_endpoint(
    workout_create: WorkoutCreate,
    force: bool = False,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Create a new planned workout.
    """
    try:
        new_w = service.add_workout(workout_create, user=user, force=force)
        return {"status": "success", "message": "Workout created", "id": new_w.id}
    except ValidationWarningError as e:
        return JSONResponse(
            status_code=409,
            content={
                "status": "warning",
                "message": e.message,
                "issues": [asdict(i) for i in e.issues],
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/workouts/{workout_id}")
async def update_workout_endpoint(
    workout_id: int,
    update_data: WorkoutUpdate,
    force: bool = False,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Update a specific workout (distance, type, description, etc).
    """
    try:
        updated = service.update_workout(workout_id, update_data, force=force)
        return {"status": "success", "message": "Workout updated", "id": updated.id}
    except ValidationWarningError as e:
        return JSONResponse(
            status_code=409,
            content={
                "status": "warning",
                "message": e.message,
                "issues": [asdict(i) for i in e.issues],
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/workouts/{workout_id}")
async def delete_workout_endpoint(
    workout_id: int,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Delete a specific planned workout.
    """
    try:
        service.delete_workout(workout_id)
        return {"status": "success", "message": "Workout deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/garmin/token", response_model=GarminToken, tags=["Garmin"])
def get_garmin_token(creds: GarminLogin):
    """
    Authenticate with Garmin Connect using credentials and return an OAuth token archive.
    The credentials are not stored on the server.
    """
    try:
        # Use static method, no session needed for login generation
        token_str = GarminService.generate_tokens(creds.email, creds.password)
        return {"token": token_str}
    except ValueError as e:
        logger.warning(f"Garmin auth failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Garmin auth internal error: {e}")
        raise HTTPException(status_code=500, detail="Internal Service Error")
