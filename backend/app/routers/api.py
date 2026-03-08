from fastapi import APIRouter
from app.routers import plans, strava, garmin, wizard, flags, activities

router = APIRouter()

router.include_router(plans.router)
router.include_router(strava.router)
router.include_router(garmin.router)
router.include_router(wizard.router)
router.include_router(flags.router)
router.include_router(activities.router)
