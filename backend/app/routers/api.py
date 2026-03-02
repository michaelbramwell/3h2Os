from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session, select
import os
from typing import List, Optional

from app.core.database import get_session, User
from app.core.auth import verify_jwt_middleware, require_role, allow_anonymous
from app.services.plans import PlanService
from app.services.plan_builder import PlanBuilderService
from app.services.context import ContextService
from app.services.activities import ActivityService
from app.services.garmin import GarminService
from app.services.strava import StravaService
from app.services.feature_flags import FeatureFlagService
from app.core.validation import ValidationWarningError
from dataclasses import asdict
from app.schemas import (
    WeekSchema,
    WeekUpdate,
    PlanUpdateResponse,
    ContextSchema,
    ActivitySchema,
    PlanCreate,
    WorkoutUpdate,
    WorkoutCreate,
    GarminLogin,
    GarminToken,
    WizardInput,
    PlanPreview,
    ClonePlanRequest,
    FeatureFlagSchema,
    FeatureFlagUpdate,
    UserFlagsResponse,
    StravaAuthUrlResponse,
    StravaStatusResponse,
    StravaExchangeRequest,
    StravaExchangeResponse,
    WizardDefaultsResponse,
    WizardAthleteProfileDefaults,
    WizardGoalsFocusDefaults,
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


def get_strava_service(session: Session = Depends(get_session)) -> StravaService:
    return StravaService(session)


def get_plan_builder_service(
    session: Session = Depends(get_session),
) -> PlanBuilderService:
    return PlanBuilderService(session)


def get_feature_flag_service(
    session: Session = Depends(get_session),
) -> FeatureFlagService:
    return FeatureFlagService(session)


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
    wizard_input_json: Optional[str] = None

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


@router.post("/plan.json", response_model=PlanUpdateResponse)
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
    # Use service method to determine filter types based on active plan
    filter_types = plan_service.get_active_plan_activity_types(user)
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
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
                user=user,
            )

            # Import Garmin user profile (birthday, weight, gender) into RunnerProfile.
            # Non-blocking — errors are logged, not raised.
            try:
                garmin_service.fetch_user_profile(user.id)
            except Exception as gpe:
                logger.warning(f"Garmin profile import failed (non-fatal): {gpe}")

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


@router.put("/weeks/{week_id}")
async def update_week_endpoint(
    week_id: int,
    update_data: WeekUpdate,
    service: PlanService = Depends(get_plan_service),
    user: User = Depends(get_current_user),
):
    """
    Update a specific week (e.g., status).
    """
    try:
        updated = service.update_week(week_id, update_data)
        return {"status": "success", "message": "Week updated", "id": updated.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


# ===========================================================================
# WIZARD ENDPOINTS
# ===========================================================================


@router.post("/plans/generate-preview", response_model=PlanPreview)
async def wizard_preview(
    wizard_input: WizardInput,
    user: User = Depends(get_current_user),
    service: PlanBuilderService = Depends(get_plan_builder_service),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Generate a plan preview from wizard inputs without saving to the database.
    Returns phase breakdown, volume curve, and calculated zones.
    """
    try:
        if wizard_input.sport_event.sport == "swimming" and not flag_service.is_enabled(
            "isSwimmingEnabled", user
        ):
            raise HTTPException(
                status_code=403,
                detail="Swimming plans are not enabled for your account.",
            )
        return service.generate_preview(wizard_input)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating plan preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans/from-wizard")
async def wizard_create_plan(
    wizard_input: WizardInput,
    service: PlanBuilderService = Depends(get_plan_builder_service),
    user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Generate a full plan from wizard inputs and save it to the database.
    Updates runner profile and project with wizard data.
    """
    try:
        if wizard_input.sport_event.sport == "swimming" and not flag_service.is_enabled(
            "isSwimmingEnabled", user
        ):
            raise HTTPException(
                status_code=403,
                detail="Swimming plans are not enabled for your account.",
            )
        plan = service.generate_plan(wizard_input, user)
        return {
            "status": "success",
            "message": "Plan created from wizard",
            "id": plan.id,
            "title": plan.title,
            "type": plan.type,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating plan from wizard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}/wizard-settings")
async def get_plan_wizard_settings(
    plan_id: int,
    service: PlanBuilderService = Depends(get_plan_builder_service),
    user: User = Depends(get_current_user),
):
    """
    Retrieve the wizard settings used to create a plan, so the wizard can be
    re-opened in edit mode.
    """
    try:
        wizard_input = service.get_wizard_settings(plan_id, user)
        if wizard_input is None:
            raise HTTPException(
                status_code=404,
                detail="No wizard settings found for this plan. It may have been created manually.",
            )
        return wizard_input
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting wizard settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}/from-wizard")
async def wizard_update_plan(
    plan_id: int,
    wizard_input: WizardInput,
    service: PlanBuilderService = Depends(get_plan_builder_service),
    user: User = Depends(get_current_user),
    flag_service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Re-generate a plan from updated wizard inputs, replacing the existing plan's
    weeks/workouts. Updates runner profile and project with wizard data.
    """
    try:
        if wizard_input.sport_event.sport == "swimming" and not flag_service.is_enabled(
            "isSwimmingEnabled", user
        ):
            raise HTTPException(
                status_code=403,
                detail="Swimming plans are not enabled for your account.",
            )
        plan = service.update_plan_from_wizard(plan_id, wizard_input, user)
        return {
            "status": "success",
            "message": "Plan updated from wizard",
            "id": plan.id,
            "title": plan.title,
            "type": plan.type,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating plan from wizard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans/{plan_id}/clone")
async def clone_plan(
    plan_id: int,
    clone_request: ClonePlanRequest,
    service: PlanBuilderService = Depends(get_plan_builder_service),
    user: User = Depends(get_current_user),
):
    """
    Clone an existing plan with an optional date offset.
    """
    try:
        cloned = service.clone_plan(plan_id, clone_request, user)
        return {
            "status": "success",
            "message": "Plan cloned",
            "id": cloned.id,
            "title": cloned.title,
            "type": cloned.type,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cloning plan: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================================================
# FEATURE FLAGS ENDPOINTS
# ===========================================================================


@router.get("/flags", response_model=UserFlagsResponse)
async def get_flags_for_current_user(
    user: User = Depends(get_current_user),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Return all feature flags resolved to True/False for the current user.
    Example response: {"flags": {"isSwimmingEnabled": false}}
    """
    try:
        flags = service.get_flags_for_user(user)
        return UserFlagsResponse(flags=flags)
    except Exception as e:
        logger.error(f"Error getting feature flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


import os as _os

_ADMIN_ROLE = _os.getenv("ADMIN_ROLE", "app_admin")


@router.get("/admin/flags", response_model=List[FeatureFlagSchema])
async def admin_list_flags(
    _: None = Depends(require_role(_ADMIN_ROLE)),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Admin: list all feature flags with their raw enabled_for configuration.
    Requires the '{ADMIN_ROLE}' Keycloak realm role (default: 'app_admin').
    """
    try:
        import json

        flags = service.list_flags()
        return [
            FeatureFlagSchema(
                id=f.id,
                name=f.name,
                enabled_for=json.loads(f.enabled_for_json or "[]"),
                description=f.description,
            )
            for f in flags
        ]
    except Exception as e:
        logger.error(f"Error listing flags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/flags/{flag_name}", response_model=FeatureFlagSchema)
async def admin_set_flag(
    flag_name: str,
    payload: FeatureFlagUpdate,
    _: None = Depends(require_role(_ADMIN_ROLE)),
    service: FeatureFlagService = Depends(get_feature_flag_service),
):
    """
    Admin: create or update a feature flag.
    Pass enabled_for=["*"] to enable for all, [] to disable, or a list of user types.
    Requires the '{ADMIN_ROLE}' Keycloak realm role (default: 'app_admin').
    """
    try:
        import json

        flag = service.set_flag(flag_name, payload.enabled_for, payload.description)
        return FeatureFlagSchema(
            id=flag.id,
            name=flag.name,
            enabled_for=json.loads(flag.enabled_for_json or "[]"),
            description=flag.description,
        )
    except Exception as e:
        logger.error(f"Error setting flag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Strava integration
# ---------------------------------------------------------------------------


@router.get("/strava/auth-url", response_model=StravaAuthUrlResponse, tags=["Strava"])
async def strava_auth_url(
    user: User = Depends(get_current_user),
    strava: StravaService = Depends(get_strava_service),
):
    """Return the Strava OAuth authorization URL for the current user."""
    return StravaAuthUrlResponse(url=strava.get_auth_url(user.id))


@router.post("/strava/exchange", response_model=StravaExchangeResponse, tags=["Strava"])
async def strava_exchange(
    body: StravaExchangeRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Exchange a Strava authorization code for tokens.
    Called by the frontend after Strava redirects back with ?code=&state=.
    Requires a valid JWT — the user is already authenticated.
    The state token is verified as CSRF protection only; the user identity
    comes from the JWT via get_current_user.
    """
    from app.services.strava import verify_state_token

    try:
        verify_state_token(body.state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid state token: {e}")

    try:
        strava = StravaService(session)
        token_data = strava.exchange_code(body.code)
        strava.save_token(user.id, token_data)

        try:
            strava.merge_athlete_profile(user.id, token_data["access_token"])
        except Exception as e:
            logger.warning(f"Strava athlete profile merge failed (non-fatal): {e}")

        return StravaExchangeResponse(ok=True)
    except Exception as e:
        logger.error(f"Strava exchange error: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Strava token exchange failed")


@router.get("/strava/status", response_model=StravaStatusResponse, tags=["Strava"])
async def strava_status(
    user: User = Depends(get_current_user),
    strava: StravaService = Depends(get_strava_service),
):
    """Return whether the current user has Strava connected."""
    token = strava.get_token(user.id)
    if not token:
        return StravaStatusResponse(connected=False)
    return StravaStatusResponse(
        connected=True,
        athlete_id=token.athlete_id,
        scope=token.scope,
    )


@router.delete("/strava/disconnect", tags=["Strava"])
async def strava_disconnect(
    user: User = Depends(get_current_user),
    strava: StravaService = Depends(get_strava_service),
):
    """Disconnect Strava by deleting the stored token."""
    strava.disconnect(user.id)
    return {"status": "disconnected"}


@router.post("/integrations/strava/sync", tags=["Strava"])
async def sync_strava_activities(
    days: int = 7,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Sync Strava activities for the past N days.
    Fetches activities, enriches zones, then saves via ActivityService (with precedence logic).
    Also triggers recalculate_plan_progression on the active plan, same as Garmin sync.
    """
    strava = StravaService(session)

    # Load zone thresholds from user profile for stream-based zone computation
    hr_thresholds = []
    pace_thresholds = []
    power_thresholds = []
    try:
        import json

        ctx_service = ContextService(session)
        ctx = ctx_service.get_context(user=user)
        if ctx.runner and ctx.runner.trainingZones:
            if ctx.runner.trainingZones.hr:
                hr_thresholds = [z.model_dump() for z in ctx.runner.trainingZones.hr]
            if ctx.runner.trainingZones.pace:
                pace_thresholds = [
                    z.model_dump() for z in ctx.runner.trainingZones.pace
                ]
    except Exception as e:
        logger.warning(f"Could not load zone thresholds for Strava sync: {e}")

    try:
        activities = strava.sync_activities(
            user=user,
            days=days,
            hr_thresholds=hr_thresholds,
            pace_thresholds=pace_thresholds,
            power_thresholds=power_thresholds,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Strava sync error for user {user.username}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Strava API error: {str(e)}")

    activity_service = ActivityService(session)
    saved_count = activity_service.save_activities(activities, user=user)

    # Recalculate plan progression (same as Garmin sync)
    try:
        plan_service = PlanService(session)
        plan_service.recalculate_plan_progression(user)
    except Exception as e:
        logger.warning(f"Could not recalculate plan progression after Strava sync: {e}")

    return {"synced": saved_count, "days": days}


# ---------------------------------------------------------------------------
# Strava webhooks
# ---------------------------------------------------------------------------


@router.get("/strava/webhook", tags=["Strava"])
@allow_anonymous
async def strava_webhook_verify(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None,
):
    """
    Strava webhook subscription verification (GET handshake).
    Strava sends hub.mode=subscribe, hub.challenge=<random>, hub.verify_token=<our token>.
    We must echo back hub.challenge if the verify token matches.
    Set STRAVA_WEBHOOK_VERIFY_TOKEN in env to a secret string of your choice.
    """
    expected_token = os.environ.get("STRAVA_WEBHOOK_VERIFY_TOKEN", "")
    if hub_mode == "subscribe" and hub_challenge and hub_verify_token == expected_token:
        return JSONResponse({"hub.challenge": hub_challenge})
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/strava/webhook", tags=["Strava"])
@allow_anonymous
async def strava_webhook_event(
    request: Request,
    session: Session = Depends(get_session),
):
    """
    Strava webhook event receiver (POST).
    Handles:
    - athlete deauthorization: deletes the stored token so we hold no data for revoked users.
    - activity create/update: triggers a short sync for the affected athlete.
    Strava requires a 200 response within 2 seconds; all heavy work is fire-and-forget.
    """
    try:
        event = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    object_type = event.get("object_type")
    aspect_type = event.get("aspect_type")
    owner_id = event.get("owner_id")  # Strava athlete_id

    logger.info(
        f"Strava webhook: object_type={object_type} aspect_type={aspect_type} owner_id={owner_id}"
    )

    # Deauthorization: athlete has revoked access — delete their token immediately.
    # Strava sends: object_type="athlete", aspect_type="update", updates={"authorized": "false"}
    updates = event.get("updates", {})
    if (
        object_type == "athlete"
        and aspect_type == "update"
        and updates.get("authorized") == "false"
    ):
        if owner_id:
            from app.core.database import StravaToken

            token = session.exec(
                select(StravaToken).where(StravaToken.athlete_id == owner_id)
            ).first()
            if token:
                session.delete(token)
                session.commit()
                logger.info(
                    f"Deleted Strava token for athlete_id={owner_id} (deauthorized via webhook)"
                )
        return {"status": "ok"}

    # Activity created or updated: trigger a short re-sync for the owning user
    if object_type == "activity" and aspect_type in ("create", "update"):
        if owner_id:
            from app.core.database import StravaToken

            token = session.exec(
                select(StravaToken).where(StravaToken.athlete_id == owner_id)
            ).first()
            if token:
                try:
                    strava = StravaService(session)
                    user = session.exec(
                        select(User).where(User.id == token.user_id)
                    ).first()
                    if user:
                        activities = strava.sync_activities(user=user, days=2)
                        activity_service = ActivityService(session)
                        activity_service.save_activities(activities, user=user)
                        plan_service = PlanService(session)
                        plan_service.recalculate_plan_progression(user)
                except Exception as e:
                    logger.warning(
                        f"Webhook-triggered sync failed for athlete_id={owner_id}: {e}"
                    )
        return {"status": "ok"}

    # All other event types — acknowledge and ignore
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Wizard defaults
# ---------------------------------------------------------------------------


@router.get("/wizard/defaults", response_model=WizardDefaultsResponse)
async def get_wizard_defaults(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Return partial wizard defaults seeded from the stored RunnerProfile and recent
    activity history.  All fields are Optional — only populated fields are returned.
    The frontend merges these on top of its own hardcoded defaults.

    Priority: Strava data > Garmin data > wizard-submitted data (already stored on profile).
    This endpoint simply reads whatever is currently in RunnerProfile; the priority
    was enforced at import time by merge_athlete_profile / GarminService.fetch_user_profile.
    """
    import json
    from app.core.database import RunnerProfile, ActualActivity
    from datetime import date as date_type, timedelta
    from sqlmodel import select

    profile = session.exec(
        select(RunnerProfile).where(RunnerProfile.user_id == user.id)
    ).first()

    athlete_defaults = WizardAthleteProfileDefaults()
    goals_defaults = WizardGoalsFocusDefaults()

    if profile:
        # age — compute from birthday if available, else use stored age
        if profile.birthday:
            today = date_type.today()
            bday = profile.birthday
            age = (
                today.year
                - bday.year
                - ((today.month, today.day) < (bday.month, bday.day))
            )
            athlete_defaults.age = age
        elif profile.age:
            athlete_defaults.age = profile.age

        if profile.weight_kg:
            athlete_defaults.weight_kg = profile.weight_kg

        if profile.experience_level:
            athlete_defaults.experience_level = profile.experience_level

        if profile.events_completed_json:
            try:
                events_map = json.loads(profile.events_completed_json)
                # Sum all completed events as a scalar for the wizard's events_completed field
                total = sum(int(v) for v in events_map.values() if v)
                athlete_defaults.events_completed = total
            except Exception:
                pass

        # Training zones
        if profile.training_zones_json:
            try:
                zones = json.loads(profile.training_zones_json)
                hr_zones = zones.get("hr", [])
                if hr_zones:
                    athlete_defaults.use_calculated_zones = False
                    athlete_defaults.custom_zones = {"heartRate": hr_zones}
            except Exception:
                pass

        if profile.weekly_availability:
            goals_defaults.weekly_availability = profile.weekly_availability

        if profile.pain_points_json:
            try:
                goals_defaults.pain_points = json.loads(profile.pain_points_json)
            except Exception:
                pass

        # longest_recent_distance_m — from stored profile value OR from recent activities
        if profile.longest_recent_distance_m:
            goals_defaults.longest_recent_distance_m = profile.longest_recent_distance_m
        else:
            # Compute from running activities in the last 30 days
            try:
                cutoff = date_type.today() - timedelta(days=30)
                recent_runs = session.exec(
                    select(ActualActivity).where(
                        ActualActivity.user_id == user.id,
                        ActualActivity.type.in_(["running", "trail_running"]),
                        ActualActivity.date >= cutoff,
                    )
                ).all()
                if recent_runs:
                    max_dist = max(int(a.distance_m) for a in recent_runs)
                    if max_dist > 0:
                        goals_defaults.longest_recent_distance_m = max_dist
            except Exception as e:
                logger.warning(f"Could not compute longest_recent_distance_m: {e}")

    return WizardDefaultsResponse(
        athlete_profile=athlete_defaults,
        goals_focus=goals_defaults,
    )
