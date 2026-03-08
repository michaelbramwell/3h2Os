from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
import logging

from app.core.database import User, get_session
from app.routers.deps import get_current_user
from app.services.plan_builder import PlanBuilderService
from app.services.feature_flags import FeatureFlagService
from app.schemas import (
    WizardInput,
    PlanPreview,
    ClonePlanRequest,
    WizardDefaultsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Wizard"])


def get_plan_builder_service(
    session: Session = Depends(get_session),
) -> PlanBuilderService:
    return PlanBuilderService(session)


def get_feature_flag_service(
    session: Session = Depends(get_session),
) -> FeatureFlagService:
    return FeatureFlagService(session)


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


@router.get("/wizard/defaults", response_model=WizardDefaultsResponse)
async def get_wizard_defaults(
    user: User = Depends(get_current_user),
    service: PlanBuilderService = Depends(get_plan_builder_service),
):
    """
    Return partial wizard defaults seeded from the stored RunnerProfile and recent
    activity history.  All fields are Optional — only populated fields are returned.
    The frontend merges these on top of its own hardcoded defaults.
    """
    return service.get_wizard_defaults(user)
