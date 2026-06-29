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
from typing import Dict, Any, Optional

from sqlmodel import Session, select

from app.core.database import (
    User,
    RunnerPlan,
    PlanWeek,
    RunnerProfile,
    RunnerProject,
)
from app.core.plan_context import project_snapshot_from_wizard
from app.core.templates import (
    RUNNING_TEMPLATES,
    SWIMMING_TEMPLATES,
    generate_plan_from_template,
    calculate_phase_structure,
)
from app.core.templates.base import get_preview_volumes, _apply_taper_weeks_override
from app.core.zones import calculate_zones
from app.schemas import WizardInput, PlanPreview, PhasePreview, ClonePlanRequest
from app.services.plans import PlanService


class PlanBuilderService:
    def __init__(self, session: Session):
        self.session = session
        self.plan_service = PlanService(session)

    # ------------------------------------------------------------------
    # Wizard Defaults
    # ------------------------------------------------------------------

    def get_wizard_defaults(self, user: User) -> "WizardDefaultsResponse":
        """
        Return partial wizard defaults seeded from the stored RunnerProfile and recent
        activity history. All fields are Optional — only populated fields are returned.
        The frontend merges these on top of its own hardcoded defaults.
        """
        import json
        import logging
        from datetime import date as date_type, timedelta
        from app.core.database import RunnerProfile, ActualActivity
        from app.schemas import (
            WizardAthleteProfileDefaults,
            WizardGoalsFocusDefaults,
            WizardDefaultsResponse,
        )

        logger = logging.getLogger(__name__)

        profile = self.session.exec(
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
                goals_defaults.longest_recent_distance_m = (
                    profile.longest_recent_distance_m
                )
            else:
                # Compute from running activities in the last 30 days
                try:
                    cutoff = date_type.today() - timedelta(days=30)
                    recent_runs = self.session.exec(
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
        return wizard.sport_event.plan_name

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
            # Align to Monday (snap backward so the plan doesn't overshoot the event)
            if start.weekday() != 0:
                start = start - timedelta(days=start.weekday())
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

    def generate_preview(
        self, wizard: WizardInput, is_edit: bool = False
    ) -> PlanPreview:
        """Generate a plan preview without saving to the database."""
        sport = wizard.sport_event.sport
        event_type = wizard.sport_event.event_type
        level = wizard.athlete_profile.experience_level
        total_weeks = wizard.plan_config.total_weeks

        # Reject plans that would start in the past — skip this check in edit mode
        # because an in-progress plan's calculated start will always be in the past.
        if not is_edit and wizard.sport_event.event_date:
            preview_start = self._calculate_start_date(
                wizard.sport_event.event_date, total_weeks
            )
            if preview_start < date.today():
                raise ValueError(
                    f"Plan would start on {preview_start.isoformat()} which is in the past. "
                    "Reduce the plan length or move the event date."
                )

        if event_type == "none":
            raise ValueError(
                "Template generation is not supported for 'none' event type."
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
        try:
            from app.models.domain import EventType, EVENT_DISTANCES_M

            race_distance_m = EVENT_DISTANCES_M.get(
                EventType(wizard.sport_event.event_type)
            )
        except (ValueError, KeyError):
            race_distance_m = None

        weekly_volumes = get_preview_volumes(
            template,
            total_weeks,
            taper_weeks_override=taper_weeks,
            race_distance_m=race_distance_m,
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

    def _generate_plan_data(
        self,
        wizard: WizardInput,
        is_edit: bool = False,
        start_date_override: Optional[date] = None,
    ):
        """Helper to generate plan data from wizard input."""
        sport = wizard.sport_event.sport
        event_type = wizard.sport_event.event_type
        level = wizard.athlete_profile.experience_level
        total_weeks = wizard.plan_config.total_weeks

        if event_type == "none":
            raise ValueError(
                "Template generation is not supported for 'none' event type."
            )

        template = self._resolve_template(event_type, level, sport)

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

        # Determine start date — prefer an explicit override (edit mode preserves the
        # existing plan's original start) over a fresh calculation.
        if start_date_override is not None:
            start_date = start_date_override
        else:
            start_date = self._calculate_start_date(
                wizard.sport_event.event_date, total_weeks
            )

        # Reject plans that would start in the past — skip in edit mode
        if not is_edit and start_date < date.today():
            raise ValueError(
                f"Plan would start on {start_date.isoformat()} which is in the past. "
                "Reduce the plan length or move the event date."
            )

        # Generate plan data
        return generate_plan_from_template(
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

    def generate_plan(self, wizard: WizardInput, user: User) -> RunnerPlan:
        """Generate a full plan from wizard inputs and persist it."""
        sport = wizard.sport_event.sport
        zones = self._calculate_zones(wizard)

        plan_data = self._generate_plan_data(wizard)

        # Build title
        title = self._build_plan_title(wizard)

        # Persist plan via PlanService
        plan = self.plan_service.create_or_update_plan(
            plan_data=plan_data,
            user=user,
            title=title,
            plan_type=sport,
            activate=True,
            wizard_input=wizard,
        )

        # Update profile and project
        self._update_profile(wizard, user, zones)
        self._update_project(wizard, user, plan)

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
        else:
            profile.pain_points_json = "[]"

        # Zones
        if wizard.sport_event.sport == "swimming":
            profile.swim_zones_json = json.dumps(zones)
        else:
            profile.training_zones_json = json.dumps(zones)

        self.session.add(profile)
        self.session.commit()

    def _update_project(
        self, wizard: WizardInput, user: User, plan: "RunnerPlan" = None
    ) -> None:
        """Create or update the runner project with wizard data.

        Also snapshots event/goal/event_date onto the RunnerPlan so that
        activate_plan can restore them when switching between plans.
        """
        project = self.session.exec(
            select(RunnerProject).where(RunnerProject.user_id == user.id)
        ).first()

        snapshot = project_snapshot_from_wizard(wizard)

        if not project:
            project = RunnerProject(
                user_id=user.id,
                name=snapshot["name"],
                goal=snapshot["goal"],
                event=snapshot["event"],
                event_date=snapshot["event_date"],
            )

        project.name = snapshot["name"]
        project.goal = snapshot["goal"]
        project.event = snapshot["event"]
        project.event_date = snapshot["event_date"]
        project.event_type = wizard.sport_event.event_type
        project.target_time = wizard.goals_focus.target_time
        project.primary_goal = wizard.goals_focus.primary_goal

        self.session.add(project)

        # Snapshot project context onto the plan
        if plan:
            plan.event = snapshot["event"]
            plan.goal = snapshot["goal"]
            plan.event_date = snapshot["event_date"]
            plan.wizard_input_json = wizard.model_dump_json()
            self.session.add(plan)

        self.session.commit()

    # ------------------------------------------------------------------
    # Clone plan
    # ------------------------------------------------------------------

    def get_wizard_settings(self, plan_id: int, user: User) -> Optional[Dict[str, Any]]:
        """Retrieve the stored wizard input for an existing plan."""
        plan = self.session.get(RunnerPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        if plan.user_id != user.id:
            raise ValueError("Cannot access a plan that does not belong to you")

        if not plan.wizard_input_json:
            # Synthesize a minimal WizardInput for legacy manual plans that
            # pre-date wizard_input_json persistence.  This allows the manual
            # builder to open and edit them without a 404.
            sport = plan.type if plan.type in ("running", "swimming") else "running"
            return {
                "sport_event": {
                    "plan_name": plan.title,
                    "sport": sport,
                    "event_type": "none",
                    "event_name": None,
                    "event_date": None,
                },
                "athlete_profile": {
                    "experience_level": "intermediate",
                    "age": 35,
                    "weight_kg": 70.0,
                    "events_completed": 0,
                    "preferred_time_of_day": None,
                    "preferred_training_days": None,
                    "preferred_long_run_day": None,
                    "use_calculated_zones": True,
                    "custom_zones": None,
                },
                "goals_focus": {
                    "primary_goal": "finish",
                    "target_time": None,
                    "pain_points": [],
                    "weekly_availability": 5,
                    "longest_recent_distance_m": 0,
                },
                "plan_config": {
                    "total_weeks": 14,
                    "taper_weeks": None,
                    "generation_method": "manual",
                },
            }

        return json.loads(plan.wizard_input_json)

    def update_plan_from_wizard(
        self, plan_id: int, wizard: WizardInput, user: User
    ) -> RunnerPlan:
        """Re-generate a plan from updated wizard inputs, replacing the existing plan."""
        plan = self.session.get(RunnerPlan, plan_id)
        if not plan:
            raise ValueError(f"Plan with ID {plan_id} not found")
        if plan.user_id != user.id:
            raise ValueError("Cannot update a plan that does not belong to you")

        # Anchor to the existing plan's original start date so that an in-progress
        # plan retains its full length rather than being recalculated from event_date.
        existing_start = self.session.exec(
            select(PlanWeek.start_date)
            .where(PlanWeek.plan_id == plan_id)
            .order_by(PlanWeek.start_date)
        ).first()

        sport = wizard.sport_event.sport
        zones = self._calculate_zones(wizard)
        plan_data = self._generate_plan_data(
            wizard, is_edit=True, start_date_override=existing_start
        )

        self.plan_service.rewrite_existing_plan(
            plan,
            plan_data,
            title=self._build_plan_title(wizard),
            plan_type=sport,
            wizard_input=wizard,
            sync_project_context=False,
        )

        # Update profile and project
        self._update_profile(wizard, user, zones)
        self._update_project(wizard, user, plan)

        return plan

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
