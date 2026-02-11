"""
Plan builder service -- translates wizard inputs into generated training plans.

Responsibilities:
- Look up the correct template from RUNNING_TEMPLATES / SWIMMING_TEMPLATES
- Calculate training zones via the zone calculator
- Generate a plan skeleton via the template engine
- Update RunnerProfile and RunnerProject with wizard data
- Persist the generated plan via PlanService
- Handle clone plan logic
"""

import json
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from sqlmodel import Session, select

from app.core.database import (
    User,
    RunnerPlan,
    RunnerProfile,
    RunnerProject,
    PlanWeek,
    PlanWorkout,
)
from app.core.templates import (
    RUNNING_TEMPLATES,
    SWIMMING_TEMPLATES,
    generate_plan_from_template,
    calculate_phase_structure,
)
from app.core.templates.base import get_preview_volumes, _apply_taper_weeks_override
from app.core.zones import calculate_zones
from app.models.domain import (
    RUNNING_EVENTS,
    SWIMMING_EVENTS,
    EventType,
    EVENT_DISTANCES_M,
)
from app.schemas import WizardInput, PlanPreview, PhasePreview, ClonePlanRequest
from app.services.plans import PlanService


class PlanBuilderService:
    def __init__(self, session: Session):
        self.session = session
        self.plan_service = PlanService(session)

    # ------------------------------------------------------------------
    # Template lookup
    # ------------------------------------------------------------------

    def _resolve_template(self, event_type: str, level: str, sport: str):
        """Find the best matching template for the given event/level/sport."""
        key = (event_type, level)

        if sport == "running":
            template = RUNNING_TEMPLATES.get(key)
            if not template:
                # Fallback: try intermediate for the same event
                template = RUNNING_TEMPLATES.get((event_type, "intermediate"))
            if not template:
                # Last resort: marathon intermediate
                template = RUNNING_TEMPLATES[("marathon", "intermediate")]
            return template

        if sport == "swimming":
            template = SWIMMING_TEMPLATES.get(key)
            if not template:
                template = SWIMMING_TEMPLATES.get((event_type, "intermediate"))
            if not template:
                # Last resort: pool 1500 intermediate
                template = SWIMMING_TEMPLATES[("pool_1500m", "intermediate")]
            return template

        raise ValueError(f"Unknown sport: {sport}")

    # ------------------------------------------------------------------
    # Zones
    # ------------------------------------------------------------------

    def _calculate_zones(self, wizard: WizardInput) -> Dict[str, Any]:
        """Calculate or pass-through custom training zones."""
        profile = wizard.athlete_profile
        sport_event = wizard.sport_event

        if not profile.use_calculated_zones and profile.custom_zones:
            return profile.custom_zones

        return calculate_zones(
            age=profile.age,
            experience_level=profile.experience_level,
            sport=sport_event.sport,
            event_type=sport_event.event_type,
            target_time=wizard.goals_focus.target_time,
        )

    # ------------------------------------------------------------------
    # Plan title
    # ------------------------------------------------------------------

    def _build_plan_title(self, wizard: WizardInput) -> str:
        """Generate a human-readable plan title from wizard inputs."""
        event_type = wizard.sport_event.event_type
        level = wizard.athlete_profile.experience_level

        # Humanise the event type
        event_labels = {
            "5k": "5K",
            "10k": "10K",
            "half_marathon": "Half Marathon",
            "marathon": "Marathon",
            "ultra": "Ultra",
            "pool_400m": "400m Pool",
            "pool_800m": "800m Pool",
            "pool_1500m": "1500m Pool",
            "ow_1km": "1km Open Water",
            "ow_2.5km": "2.5km Open Water",
            "ow_5km": "5km Open Water",
            "ow_10km": "10km Open Water",
        }
        event_label = event_labels.get(event_type, event_type)
        level_label = level.capitalize()

        if wizard.sport_event.event_name:
            return f"{wizard.sport_event.event_name} - {level_label} {event_label}"
        return f"{level_label} {event_label} Plan"

    # ------------------------------------------------------------------
    # Start date calculation
    # ------------------------------------------------------------------

    def _calculate_start_date(
        self, event_date: Optional[date], total_weeks: int
    ) -> date:
        """
        Determine plan start date.
        If an event date is given, count back total_weeks from it.
        Otherwise start next Monday.
        """
        if event_date:
            start = event_date - timedelta(weeks=total_weeks)
            # Align to Monday
            days_until_monday = (7 - start.weekday()) % 7
            if days_until_monday == 0 and start.weekday() != 0:
                days_until_monday = 7
            start = (
                start + timedelta(days=days_until_monday)
                if start.weekday() != 0
                else start
            )
            return start

        # No event date: start next Monday
        today = date.today()
        days_ahead = (7 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return today + timedelta(days=days_ahead)

    # ------------------------------------------------------------------
    # Preview (no DB write)
    # ------------------------------------------------------------------

    def generate_preview(self, wizard: WizardInput) -> PlanPreview:
        """Generate a plan preview without saving to the database."""
        sport = wizard.sport_event.sport
        event_type = wizard.sport_event.event_type
        level = wizard.athlete_profile.experience_level
        total_weeks = wizard.plan_config.total_weeks

        # Reject plans that would start in the past
        if wizard.sport_event.event_date:
            preview_start = self._calculate_start_date(
                wizard.sport_event.event_date, total_weeks
            )
            if preview_start < date.today():
                raise ValueError(
                    f"Plan would start on {preview_start.isoformat()} which is in the past. "
                    "Reduce the plan length or move the event date."
                )

        template = self._resolve_template(event_type, level, sport)
        zones = self._calculate_zones(wizard)

        # Phase breakdown
        phase_structure = calculate_phase_structure(
            total_weeks, template.phases, template.phase_proportions
        )

        # Apply taper weeks override if user specified one
        taper_weeks = wizard.plan_config.taper_weeks
        if taper_weeks is not None:
            _apply_taper_weeks_override(phase_structure, taper_weeks)

        phases = [
            PhasePreview(
                name=p["name"].capitalize(),
                weeks=p["weeks"],
                description=p.get("description", ""),
            )
            for p in phase_structure
        ]

        # Volume curve
        weekly_volumes = get_preview_volumes(
            template, total_weeks, taper_weeks_override=taper_weeks
        )
        peak_volume = max(weekly_volumes) if weekly_volumes else template.peak_volume_m

        # Sessions per week from the template's default build week
        build_week_tmpl = template.week_templates.get(
            "build", list(template.week_templates.values())[0]
        )
        if isinstance(build_week_tmpl, list):
            build_week_tmpl = build_week_tmpl[0]
        default_sessions = len(build_week_tmpl.sessions)
        # Clamp to availability if provided
        sessions_per_week = min(
            wizard.goals_focus.weekly_availability, default_sessions
        )

        return PlanPreview(
            title=self._build_plan_title(wizard),
            sport=sport,
            event_type=event_type,
            total_weeks=total_weeks,
            phases=phases,
            peak_weekly_volume_m=peak_volume,
            weekly_volumes_m=weekly_volumes,
            sessions_per_week=sessions_per_week,
            zones=zones,
        )

    # ------------------------------------------------------------------
    # Full generation (creates plan + updates profile/project)
    # ------------------------------------------------------------------

    def generate_plan(self, wizard: WizardInput, user: User) -> RunnerPlan:
        """Generate a full plan from wizard inputs and persist it."""
        sport = wizard.sport_event.sport
        event_type = wizard.sport_event.event_type
        level = wizard.athlete_profile.experience_level
        total_weeks = wizard.plan_config.total_weeks

        template = self._resolve_template(event_type, level, sport)
        zones = self._calculate_zones(wizard)

        # Determine sessions per week
        build_week_tmpl = template.week_templates.get(
            "build", list(template.week_templates.values())[0]
        )
        if isinstance(build_week_tmpl, list):
            build_week_tmpl = build_week_tmpl[0]
        default_sessions = len(build_week_tmpl.sessions)
        sessions_per_week = min(
            wizard.goals_focus.weekly_availability, default_sessions
        )

        # Determine start date
        start_date = self._calculate_start_date(
            wizard.sport_event.event_date, total_weeks
        )

        # Reject plans that would start in the past
        if start_date < date.today():
            raise ValueError(
                f"Plan would start on {start_date.isoformat()} which is in the past. "
                "Reduce the plan length or move the event date."
            )

        # Generate plan data
        plan_data = generate_plan_from_template(
            template=template,
            start_date=start_date,
            total_weeks=total_weeks,
            sessions_per_week=sessions_per_week,
            event_type=event_type,
            taper_weeks_override=wizard.plan_config.taper_weeks,
            preferred_time_of_day=wizard.athlete_profile.preferred_time_of_day,
            preferred_training_days=wizard.athlete_profile.preferred_training_days,
            preferred_long_run_day=wizard.athlete_profile.preferred_long_run_day,
        )

        # Build title
        title = self._build_plan_title(wizard)

        # Persist plan via PlanService
        plan = self.plan_service.create_or_update_plan(
            plan_data=plan_data,
            user=user,
            title=title,
            plan_type=sport,
            activate=True,
        )

        # Update profile and project
        self._update_profile(wizard, user, zones)
        self._update_project(wizard, user)

        return plan

    # ------------------------------------------------------------------
    # Profile / Project updates
    # ------------------------------------------------------------------

    def _update_profile(
        self, wizard: WizardInput, user: User, zones: Dict[str, Any]
    ) -> None:
        """Create or update the runner profile with wizard data."""
        profile = self.session.exec(
            select(RunnerProfile).where(RunnerProfile.user_id == user.id)
        ).first()

        if not profile:
            profile = RunnerProfile(
                user_id=user.id,
                age=wizard.athlete_profile.age,
                gender="unknown",
                height_cm=0,
            )

        profile.age = wizard.athlete_profile.age
        profile.weight_kg = wizard.athlete_profile.weight_kg
        profile.experience_level = wizard.athlete_profile.experience_level
        profile.weekly_availability = wizard.goals_focus.weekly_availability
        profile.longest_recent_distance_m = wizard.goals_focus.longest_recent_distance_m

        # Store events completed for this event type
        existing_events = {}
        if profile.events_completed_json:
            try:
                existing_events = json.loads(profile.events_completed_json)
            except (json.JSONDecodeError, TypeError):
                existing_events = {}
        existing_events[wizard.sport_event.event_type] = (
            wizard.athlete_profile.events_completed
        )
        profile.events_completed_json = json.dumps(existing_events)

        # Pain points
        if wizard.goals_focus.pain_points:
            profile.pain_points_json = json.dumps(wizard.goals_focus.pain_points)

        # Zones
        if wizard.sport_event.sport == "swimming":
            profile.swim_zones_json = json.dumps(zones)
        else:
            profile.training_zones_json = json.dumps(zones)

        self.session.add(profile)
        self.session.commit()

    def _update_project(self, wizard: WizardInput, user: User) -> None:
        """Create or update the runner project with wizard data."""
        project = self.session.exec(
            select(RunnerProject).where(RunnerProject.user_id == user.id)
        ).first()

        event_labels = {
            "5k": "5K",
            "10k": "10K",
            "half_marathon": "Half Marathon",
            "marathon": "Marathon",
            "ultra": "Ultra",
            "pool_400m": "400m Pool",
            "pool_800m": "800m Pool",
            "pool_1500m": "1500m Pool",
            "ow_1km": "1km Open Water",
            "ow_2.5km": "2.5km Open Water",
            "ow_5km": "5km Open Water",
            "ow_10km": "10km Open Water",
        }
        event_label = event_labels.get(
            wizard.sport_event.event_type, wizard.sport_event.event_type
        )

        goal_label = wizard.goals_focus.primary_goal.replace("_", " ").capitalize()
        if wizard.goals_focus.target_time:
            goal_label = f"Target: {wizard.goals_focus.target_time}"

        event_date = wizard.sport_event.event_date or (
            date.today() + timedelta(weeks=wizard.plan_config.total_weeks)
        )

        if not project:
            project = RunnerProject(
                user_id=user.id,
                name=wizard.sport_event.event_name or f"{event_label} Training",
                goal=goal_label,
                event=event_label,
                event_date=event_date,
            )

        project.name = wizard.sport_event.event_name or f"{event_label} Training"
        project.goal = goal_label
        project.event = event_label
        project.event_date = event_date
        project.event_type = wizard.sport_event.event_type
        project.target_time = wizard.goals_focus.target_time
        project.primary_goal = wizard.goals_focus.primary_goal

        self.session.add(project)
        self.session.commit()

    # ------------------------------------------------------------------
    # Clone plan
    # ------------------------------------------------------------------

    def clone_plan(
        self, plan_id: int, clone_request: ClonePlanRequest, user: User
    ) -> RunnerPlan:
        """Clone an existing plan with an optional date shift."""
        source_plan = self.session.get(RunnerPlan, plan_id)
        if not source_plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        if source_plan.user_id != user.id:
            raise ValueError("Cannot clone a plan that does not belong to you")

        # Load relational data from source plan
        from app.core.mappers import relational_to_plan

        plan_data = relational_to_plan(self.session, source_plan.id)
        if not plan_data:
            raise ValueError("Source plan has no data to clone")

        # Apply date offset if specified
        offset_days = clone_request.date_offset_days
        if offset_days != 0:
            for week in plan_data:
                if "weekStarting" in week:
                    old_date = date.fromisoformat(week["weekStarting"])
                    new_date = old_date + timedelta(days=offset_days)
                    week["weekStarting"] = new_date.strftime("%Y-%m-%d")
                if "days" in week:
                    for day_name, day_data in week["days"].items():
                        if "date" in day_data:
                            old_date = date.fromisoformat(day_data["date"])
                            new_date = old_date + timedelta(days=offset_days)
                            day_data["date"] = new_date.strftime("%Y-%m-%d")

        # Create new plan (not activated by default)
        cloned = self.plan_service.create_or_update_plan(
            plan_data=plan_data,
            user=user,
            title=clone_request.new_title,
            plan_type=source_plan.type,
            activate=False,
        )

        return cloned
