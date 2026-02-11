"""
Tests for the plan builder wizard backend: zone calculator, template engine,
and PlanBuilderService.
"""

import pytest
from datetime import date, timedelta

from sqlmodel import Session, SQLModel, create_engine, select
from sqlalchemy.pool import StaticPool

from app.core.database import (
    User,
    RunnerPlan,
    RunnerProfile,
    RunnerProject,
    PlanWeek,
    PlanWorkout,
)
from app.core.zones import (
    calculate_max_hr,
    calculate_hr_zones,
    calculate_pace_zones,
    calculate_swim_pace_zones,
    calculate_zones,
    estimate_easy_pace_m_s,
)
from app.core.templates import (
    RUNNING_TEMPLATES,
    SWIMMING_TEMPLATES,
    generate_plan_from_template,
    calculate_phase_structure,
)
from app.core.templates.base import get_preview_volumes
from app.schemas import (
    WizardInput,
    WizardSportEvent,
    WizardAthleteProfile,
    WizardGoalsFocus,
    WizardPlanConfig,
    ClonePlanRequest,
)
from app.services.plan_builder import PlanBuilderService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def user(session: Session) -> User:
    u = User(username="testrunner", email="test@example.com")
    session.add(u)
    session.commit()
    session.refresh(u)
    return u


def _make_wizard_input(
    sport: str = "running",
    event_type: str = "marathon",
    level: str = "intermediate",
    age: int = 35,
    total_weeks: int = 14,
    weekly_availability: int = 5,
    primary_goal: str = "finish_strong",
    target_time: str | None = None,
    event_date: date | None = None,
    taper_weeks: int | None = None,
) -> WizardInput:
    return WizardInput(
        sport_event=WizardSportEvent(
            sport=sport,
            event_type=event_type,
            event_date=event_date,
        ),
        athlete_profile=WizardAthleteProfile(
            experience_level=level,
            age=age,
            weight_kg=75.0,
            events_completed=2,
        ),
        goals_focus=WizardGoalsFocus(
            primary_goal=primary_goal,
            target_time=target_time,
            weekly_availability=weekly_availability,
            longest_recent_distance_m=15000,
        ),
        plan_config=WizardPlanConfig(total_weeks=total_weeks, taper_weeks=taper_weeks),
    )


# ===========================================================================
# Zone Calculator Tests
# ===========================================================================


class TestMaxHR:
    def test_tanaka_formula(self):
        # 208 - 0.7 * 30 = 187
        assert calculate_max_hr(30) == 187

    def test_age_20(self):
        assert calculate_max_hr(20) == 194

    def test_age_50(self):
        assert calculate_max_hr(50) == 173

    def test_max_hr_decreases_with_age(self):
        assert calculate_max_hr(25) > calculate_max_hr(45)


class TestHRZones:
    def test_returns_five_zones(self):
        zones = calculate_hr_zones(35)
        assert len(zones) == 5

    def test_zone_numbers_sequential(self):
        zones = calculate_hr_zones(35)
        for i, z in enumerate(zones, 1):
            assert z["zone"] == i

    def test_zones_are_ascending(self):
        zones = calculate_hr_zones(35)
        for i in range(len(zones) - 1):
            assert zones[i]["lowBoundary_bpm"] < zones[i + 1]["lowBoundary_bpm"]
            assert zones[i]["highBoundary_bpm"] <= zones[i + 1]["highBoundary_bpm"]

    def test_zone_1_starts_at_50_percent(self):
        max_hr = calculate_max_hr(35)
        zones = calculate_hr_zones(35)
        assert zones[0]["lowBoundary_bpm"] == round(max_hr * 0.50)

    def test_zone_5_tops_at_100_percent(self):
        max_hr = calculate_max_hr(35)
        zones = calculate_hr_zones(35)
        assert zones[4]["highBoundary_bpm"] == max_hr

    def test_all_zones_in_sane_range(self):
        for age in [20, 30, 40, 50, 60]:
            zones = calculate_hr_zones(age)
            for z in zones:
                assert 70 <= z["lowBoundary_bpm"] <= 220
                assert 70 <= z["highBoundary_bpm"] <= 220

    def test_zone_descriptions_present(self):
        zones = calculate_hr_zones(35)
        descriptions = [z["description"] for z in zones]
        assert "Recovery" in descriptions
        assert "Aerobic" in descriptions
        assert "VO2max" in descriptions


class TestPaceZones:
    def test_returns_five_zones(self):
        zones = calculate_pace_zones("intermediate", "marathon")
        assert len(zones) == 5

    def test_zones_are_ascending_by_pace(self):
        zones = calculate_pace_zones("intermediate", "marathon")
        paces = [z["lowBoundary_m_s"] for z in zones]
        for i in range(len(paces) - 1):
            assert paces[i] < paces[i + 1], (
                f"Zone {i + 1} pace should be slower than zone {i + 2}"
            )

    def test_all_levels_produce_positive_paces(self):
        for level in ["beginner", "intermediate", "advanced"]:
            zones = calculate_pace_zones(level, "half_marathon")
            for z in zones:
                assert z["lowBoundary_m_s"] > 0

    def test_advanced_faster_than_beginner(self):
        beg = calculate_pace_zones("beginner", "10k")
        adv = calculate_pace_zones("advanced", "10k")
        # Zone 2 (easy) pace should be faster for advanced
        beg_easy = next(z for z in beg if z["zone"] == 2)["lowBoundary_m_s"]
        adv_easy = next(z for z in adv if z["zone"] == 2)["lowBoundary_m_s"]
        assert adv_easy > beg_easy

    def test_target_time_adjusts_pace(self):
        # With a fast target time, pace should differ from default
        default = calculate_pace_zones("intermediate", "marathon")
        with_target = calculate_pace_zones("intermediate", "marathon", "3:00:00")
        default_easy = next(z for z in default if z["zone"] == 2)["lowBoundary_m_s"]
        target_easy = next(z for z in with_target if z["zone"] == 2)["lowBoundary_m_s"]
        # A 3:00 marathon target is fast -- should produce faster paces
        assert target_easy != default_easy


class TestSwimPaceZones:
    def test_returns_five_zones(self):
        zones = calculate_swim_pace_zones("intermediate")
        assert len(zones) == 5

    def test_zones_ascending(self):
        zones = calculate_swim_pace_zones("beginner")
        paces = [z["lowBoundary_m_s"] for z in zones]
        for i in range(len(paces) - 1):
            assert paces[i] < paces[i + 1]

    def test_all_levels_positive(self):
        for level in ["beginner", "intermediate", "advanced"]:
            zones = calculate_swim_pace_zones(level)
            for z in zones:
                assert z["lowBoundary_m_s"] > 0

    def test_swim_paces_slower_than_running(self):
        swim = calculate_swim_pace_zones("intermediate")
        run = calculate_pace_zones("intermediate", "5k")
        # Swim zone 2 should be slower (lower m/s) than run zone 2
        swim_z2 = next(z for z in swim if z["zone"] == 2)["lowBoundary_m_s"]
        run_z2 = next(z for z in run if z["zone"] == 2)["lowBoundary_m_s"]
        assert swim_z2 < run_z2


class TestCalculateZones:
    def test_running_zones_have_hr_and_pace(self):
        zones = calculate_zones(30, "intermediate", "running", "marathon")
        assert "heartRate" in zones
        assert "pace" in zones
        assert "swimPace" not in zones

    def test_swimming_zones_have_hr_and_swim_pace(self):
        zones = calculate_zones(30, "intermediate", "swimming", "pool_1500m")
        assert "heartRate" in zones
        assert "swimPace" in zones
        assert "pace" not in zones


class TestEasyPace:
    def test_beginner_slower_than_advanced(self):
        beg = estimate_easy_pace_m_s("beginner", "marathon")
        adv = estimate_easy_pace_m_s("advanced", "marathon")
        assert beg < adv

    def test_returns_positive_float(self):
        pace = estimate_easy_pace_m_s("intermediate", "10k")
        assert isinstance(pace, float)
        assert pace > 0


# ===========================================================================
# Template Engine Tests
# ===========================================================================


class TestPhaseStructure:
    def test_total_weeks_match(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        phases = calculate_phase_structure(
            14, template.phases, template.phase_proportions
        )
        total = sum(p["weeks"] for p in phases)
        assert total == 14

    def test_total_weeks_match_short_plan(self):
        template = RUNNING_TEMPLATES[("5k", "beginner")]
        phases = calculate_phase_structure(
            8, template.phases, template.phase_proportions
        )
        total = sum(p["weeks"] for p in phases)
        assert total == 8

    def test_all_phases_have_at_least_one_week(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        phases = calculate_phase_structure(
            14, template.phases, template.phase_proportions
        )
        for p in phases:
            assert p["weeks"] >= 1

    def test_phase_names_present(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        phases = calculate_phase_structure(
            14, template.phases, template.phase_proportions
        )
        names = [p["name"] for p in phases]
        assert len(names) >= 3  # At least base/build/taper


class TestPreviewVolumes:
    def test_returns_correct_number_of_weeks(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        volumes = get_preview_volumes(template, 14)
        assert len(volumes) == 14

    def test_all_volumes_positive(self):
        template = RUNNING_TEMPLATES[("half_marathon", "beginner")]
        volumes = get_preview_volumes(template, 12)
        for v in volumes:
            assert v > 0

    def test_peak_not_exceeded(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        volumes = get_preview_volumes(template, 14)
        # Allow small float rounding
        for v in volumes:
            assert v <= template.peak_volume_m * 1.01


class TestPlanGeneration:
    def test_generates_correct_number_of_weeks(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        assert len(plan) == 14

    def test_week_starting_dates_are_mondays(self):
        template = RUNNING_TEMPLATES[("half_marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),  # Monday
            total_weeks=12,
            sessions_per_week=4,
        )
        for week in plan:
            d = date.fromisoformat(week["weekStarting"])
            assert d.weekday() == 0, f"{week['weekStarting']} is not a Monday"

    def test_each_week_has_seven_days(self):
        template = RUNNING_TEMPLATES[("10k", "beginner")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=8,
            sessions_per_week=3,
        )
        expected_days = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
        for week in plan:
            assert set(week["days"].keys()) == expected_days

    def test_workouts_have_required_fields(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        for week in plan:
            for day_name, day_data in week["days"].items():
                for workout in day_data["workouts"]:
                    assert "name" in workout
                    assert "type" in workout
                    assert "distance_m" in workout
                    assert "timeOfDay" in workout
                    assert workout["distance_m"] >= 0

    def test_sessions_per_week_respected(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        for target_sessions in [3, 4, 5]:
            plan = generate_plan_from_template(
                template=template,
                start_date=date(2026, 3, 2),
                total_weeks=14,
                sessions_per_week=target_sessions,
            )
            for week in plan:
                total_workouts = sum(
                    len(day_data["workouts"]) for day_data in week["days"].values()
                )
                assert total_workouts <= target_sessions

    def test_day_dates_are_correct(self):
        template = RUNNING_TEMPLATES[("5k", "beginner")]
        start = date(2026, 3, 2)  # Monday
        plan = generate_plan_from_template(
            template=template,
            start_date=start,
            total_weeks=8,
            sessions_per_week=3,
        )
        # Check first week's day dates
        first_week = plan[0]
        mon_date = date.fromisoformat(first_week["days"]["Mon"]["date"])
        assert mon_date == start
        sun_date = date.fromisoformat(first_week["days"]["Sun"]["date"])
        assert sun_date == start + timedelta(days=6)

    def test_week_status_values_valid(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        valid_statuses = {"normal", "recovery", "taper", "race"}
        for week in plan:
            assert week["status"] in valid_statuses, f"Invalid status: {week['status']}"

    def test_swimming_plan_generates(self):
        template = SWIMMING_TEMPLATES[("pool_1500m", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=10,
            sessions_per_week=4,
        )
        assert len(plan) == 10
        # Swimming workouts should exist
        has_workouts = False
        for week in plan:
            for day_data in week["days"].values():
                if day_data["workouts"]:
                    has_workouts = True
                    break
        assert has_workouts


class TestTemplateRegistries:
    def test_all_running_templates_accessible(self):
        for key, template in RUNNING_TEMPLATES.items():
            assert template.sport == "running"
            assert template.event_type == key[0]
            assert template.level == key[1] or template.level in [
                "intermediate",
                "advanced",
            ]  # Fallbacks

    def test_all_swimming_templates_accessible(self):
        for key, template in SWIMMING_TEMPLATES.items():
            assert template.sport == "swimming"

    def test_running_has_major_events(self):
        events = set(k[0] for k in RUNNING_TEMPLATES.keys())
        assert "marathon" in events
        assert "half_marathon" in events
        assert "5k" in events
        assert "10k" in events

    def test_templates_have_valid_peak_volume(self):
        for key, template in RUNNING_TEMPLATES.items():
            assert template.peak_volume_m > 0
            assert template.peak_volume_m <= 250000  # 250km sanity cap
        for key, template in SWIMMING_TEMPLATES.items():
            assert template.peak_volume_m > 0


# ===========================================================================
# PlanBuilderService Tests
# ===========================================================================


class TestPlanBuilderPreview:
    def test_preview_returns_correct_structure(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input()
        preview = service.generate_preview(wizard)

        assert preview.title
        assert preview.sport == "running"
        assert preview.event_type == "marathon"
        assert preview.total_weeks == 14
        assert len(preview.phases) >= 3
        assert preview.peak_weekly_volume_m > 0
        assert len(preview.weekly_volumes_m) == 14
        assert preview.sessions_per_week > 0

    def test_preview_zones_included(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input()
        preview = service.generate_preview(wizard)
        assert preview.zones is not None
        assert "heartRate" in preview.zones
        assert "pace" in preview.zones

    def test_preview_swimming(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(sport="swimming", event_type="pool_1500m")
        preview = service.generate_preview(wizard)
        assert preview.sport == "swimming"
        assert preview.zones is not None
        assert "swimPace" in preview.zones

    def test_preview_phase_weeks_sum_to_total(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(total_weeks=16)
        preview = service.generate_preview(wizard)
        total_phase_weeks = sum(p.weeks for p in preview.phases)
        assert total_phase_weeks == 16

    def test_preview_custom_zones_passthrough(self, session, user):
        service = PlanBuilderService(session)
        custom = {"heartRate": [{"zone": 1, "lowBoundary_bpm": 120}]}
        wizard = _make_wizard_input()
        wizard.athlete_profile.use_calculated_zones = False
        wizard.athlete_profile.custom_zones = custom
        preview = service.generate_preview(wizard)
        assert preview.zones == custom

    def test_preview_respects_taper_weeks_override(self, session, user):
        """Preview phases and volume curve must honour taper_weeks from config."""
        service = PlanBuilderService(session)
        for taper_len in [1, 2, 3]:
            wizard = _make_wizard_input(total_weeks=16, taper_weeks=taper_len)
            preview = service.generate_preview(wizard)
            taper_phases = [p for p in preview.phases if p.name.lower() == "taper"]
            assert len(taper_phases) == 1
            assert taper_phases[0].weeks == taper_len, (
                f"Expected taper={taper_len} weeks in preview, "
                f"got {taper_phases[0].weeks}"
            )
            # Total weeks must still match
            assert sum(p.weeks for p in preview.phases) == 16


class TestPlanBuilderGenerate:
    def test_generate_creates_plan_in_db(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input()
        plan = service.generate_plan(wizard, user)

        assert plan.id is not None
        assert plan.is_active is True
        assert plan.type == "running"
        assert "Marathon" in plan.title or "marathon" in plan.title.lower()

    def test_generate_creates_weeks_and_workouts(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(total_weeks=8, event_type="5k", level="beginner")
        plan = service.generate_plan(wizard, user)

        weeks = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).all()
        assert len(weeks) == 8

        # At least some weeks should have workouts
        total_workouts = 0
        for week in weeks:
            workouts = session.exec(
                select(PlanWorkout).where(PlanWorkout.week_id == week.id)
            ).all()
            total_workouts += len(workouts)
        assert total_workouts > 0

    def test_generate_updates_profile(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(age=32, level="advanced")
        service.generate_plan(wizard, user)

        profile = session.exec(
            select(RunnerProfile).where(RunnerProfile.user_id == user.id)
        ).first()
        assert profile is not None
        assert profile.age == 32
        assert profile.experience_level == "advanced"
        assert profile.weight_kg == 75.0

    def test_generate_updates_project(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(primary_goal="target_time", target_time="3:30:00")
        service.generate_plan(wizard, user)

        project = session.exec(
            select(RunnerProject).where(RunnerProject.user_id == user.id)
        ).first()
        assert project is not None
        assert project.event_type == "marathon"
        assert project.target_time == "3:30:00"

    def test_generate_swimming_plan(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(
            sport="swimming", event_type="pool_1500m", total_weeks=10
        )
        plan = service.generate_plan(wizard, user)

        assert plan.type == "swimming"
        weeks = session.exec(select(PlanWeek).where(PlanWeek.plan_id == plan.id)).all()
        assert len(weeks) == 10


class TestPlanBuilderTitle:
    def test_title_with_event_name(self, session):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input()
        wizard.sport_event.event_name = "Perth City to Surf 2026"
        title = service._build_plan_title(wizard)
        assert "Perth City to Surf 2026" in title

    def test_title_without_event_name(self, session):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(level="beginner", event_type="half_marathon")
        title = service._build_plan_title(wizard)
        assert "Beginner" in title
        assert "Half Marathon" in title

    def test_title_swimming(self, session):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(sport="swimming", event_type="pool_1500m")
        title = service._build_plan_title(wizard)
        assert "1500m" in title


class TestPlanBuilderStartDate:
    def test_start_date_from_event_date(self, session):
        service = PlanBuilderService(session)
        event_date = date(2026, 6, 15)  # Monday
        start = service._calculate_start_date(event_date, 14)
        # Should be 14 weeks before the event, aligned to Monday
        assert start.weekday() == 0  # Monday
        assert start < event_date

    def test_start_date_no_event_is_next_monday(self, session):
        service = PlanBuilderService(session)
        start = service._calculate_start_date(None, 14)
        assert start.weekday() == 0  # Monday
        assert start > date.today()

    def test_start_date_is_monday(self, session):
        service = PlanBuilderService(session)
        # Use a Wednesday event date
        event_date = date(2026, 7, 8)  # Wednesday
        start = service._calculate_start_date(event_date, 10)
        assert start.weekday() == 0


class TestTemplateFallback:
    def test_unknown_running_event_falls_back(self, session):
        service = PlanBuilderService(session)
        # Use an event type that may not have a direct template
        template = service._resolve_template("marathon", "advanced", "running")
        assert template is not None

    def test_unknown_swimming_event_falls_back(self, session):
        service = PlanBuilderService(session)
        template = service._resolve_template("ow_10km", "beginner", "swimming")
        assert template is not None

    def test_unknown_sport_raises(self, session):
        service = PlanBuilderService(session)
        with pytest.raises(ValueError, match="Unknown sport"):
            service._resolve_template("marathon", "intermediate", "cycling")


class TestClonePlan:
    def test_clone_creates_new_plan(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(total_weeks=8, event_type="5k", level="beginner")
        original = service.generate_plan(wizard, user)

        clone_req = ClonePlanRequest(new_title="My Clone", date_offset_days=0)
        cloned = service.clone_plan(original.id, clone_req, user)

        assert cloned.id != original.id
        assert cloned.title == "My Clone"
        assert cloned.is_active is False  # Clones are not auto-activated

    def test_clone_with_date_offset(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(
            total_weeks=8, event_type="10k", level="intermediate"
        )
        original = service.generate_plan(wizard, user)

        clone_req = ClonePlanRequest(new_title="Shifted Clone", date_offset_days=7)
        cloned = service.clone_plan(original.id, clone_req, user)

        # Get weeks from both plans
        orig_weeks = session.exec(
            select(PlanWeek)
            .where(PlanWeek.plan_id == original.id)
            .order_by(PlanWeek.start_date)
        ).all()
        clone_weeks = session.exec(
            select(PlanWeek)
            .where(PlanWeek.plan_id == cloned.id)
            .order_by(PlanWeek.start_date)
        ).all()

        assert len(clone_weeks) == len(orig_weeks)
        # Each cloned week should be 7 days later
        for orig_w, clone_w in zip(orig_weeks, clone_weeks):
            expected = orig_w.start_date + timedelta(days=7)
            assert clone_w.start_date == expected, (
                f"Expected {expected}, got {clone_w.start_date}"
            )

    def test_clone_nonexistent_plan_raises(self, session, user):
        service = PlanBuilderService(session)
        clone_req = ClonePlanRequest(new_title="Ghost", date_offset_days=0)
        with pytest.raises(ValueError, match="not found"):
            service.clone_plan(99999, clone_req, user)

    def test_clone_other_users_plan_raises(self, session, user):
        service = PlanBuilderService(session)

        # Create another user and their plan
        other_user = User(username="otheruser", email="other@example.com")
        session.add(other_user)
        session.commit()
        session.refresh(other_user)

        wizard = _make_wizard_input()
        plan = service.generate_plan(wizard, other_user)

        clone_req = ClonePlanRequest(new_title="Stolen", date_offset_days=0)
        with pytest.raises(ValueError, match="does not belong"):
            service.clone_plan(plan.id, clone_req, user)


# ===========================================================================
# Schema Validation Tests
# ===========================================================================


class TestWizardSportEventValidation:
    def test_valid_running(self):
        s = WizardSportEvent(sport="running", event_type="marathon")
        assert s.sport == "running"

    def test_valid_swimming(self):
        s = WizardSportEvent(sport="swimming", event_type="pool_1500m")
        assert s.sport == "swimming"

    def test_invalid_sport_rejects(self):
        with pytest.raises(Exception, match="sport"):
            WizardSportEvent(sport="cycling", event_type="marathon")

    def test_invalid_event_type_rejects(self):
        with pytest.raises(Exception, match="event_type"):
            WizardSportEvent(sport="running", event_type="100m_dash")

    def test_all_running_event_types_accepted(self):
        for et in ["5k", "10k", "half_marathon", "marathon", "ultra"]:
            s = WizardSportEvent(sport="running", event_type=et)
            assert s.event_type == et

    def test_all_swimming_event_types_accepted(self):
        for et in [
            "pool_400m",
            "pool_800m",
            "pool_1500m",
            "ow_1km",
            "ow_2.5km",
            "ow_5km",
            "ow_10km",
        ]:
            s = WizardSportEvent(sport="swimming", event_type=et)
            assert s.event_type == et


class TestWizardAthleteProfileValidation:
    def test_valid_profile(self):
        p = WizardAthleteProfile(experience_level="beginner", age=30, weight_kg=70.0)
        assert p.age == 30

    def test_invalid_experience_level_rejects(self):
        with pytest.raises(Exception, match="experience_level"):
            WizardAthleteProfile(experience_level="elite", age=30, weight_kg=70.0)

    def test_age_too_low_rejects(self):
        with pytest.raises(Exception, match="age"):
            WizardAthleteProfile(experience_level="intermediate", age=5, weight_kg=70.0)

    def test_age_too_high_rejects(self):
        with pytest.raises(Exception, match="age"):
            WizardAthleteProfile(
                experience_level="intermediate", age=101, weight_kg=70.0
            )

    def test_age_zero_rejects(self):
        with pytest.raises(Exception, match="age"):
            WizardAthleteProfile(experience_level="intermediate", age=0, weight_kg=70.0)

    def test_boundary_age_10_accepted(self):
        p = WizardAthleteProfile(experience_level="beginner", age=10, weight_kg=40.0)
        assert p.age == 10

    def test_boundary_age_100_accepted(self):
        p = WizardAthleteProfile(experience_level="beginner", age=100, weight_kg=70.0)
        assert p.age == 100

    def test_all_experience_levels_accepted(self):
        for level in ["beginner", "intermediate", "advanced"]:
            p = WizardAthleteProfile(experience_level=level, age=30, weight_kg=70.0)
            assert p.experience_level == level


class TestWizardGoalsFocusValidation:
    def test_valid_goals(self):
        g = WizardGoalsFocus(primary_goal="finish", weekly_availability=5)
        assert g.weekly_availability == 5

    def test_availability_zero_rejects(self):
        with pytest.raises(Exception, match="weekly_availability"):
            WizardGoalsFocus(primary_goal="finish", weekly_availability=0)

    def test_availability_eight_rejects(self):
        with pytest.raises(Exception, match="weekly_availability"):
            WizardGoalsFocus(primary_goal="finish", weekly_availability=8)

    def test_availability_negative_rejects(self):
        with pytest.raises(Exception, match="weekly_availability"):
            WizardGoalsFocus(primary_goal="finish", weekly_availability=-1)

    def test_boundary_availability_1_accepted(self):
        g = WizardGoalsFocus(primary_goal="finish", weekly_availability=1)
        assert g.weekly_availability == 1

    def test_boundary_availability_7_accepted(self):
        g = WizardGoalsFocus(primary_goal="finish", weekly_availability=7)
        assert g.weekly_availability == 7


class TestWizardPlanConfigValidation:
    def test_valid_config(self):
        c = WizardPlanConfig(total_weeks=14)
        assert c.total_weeks == 14

    def test_weeks_too_low_rejects(self):
        with pytest.raises(Exception, match="total_weeks"):
            WizardPlanConfig(total_weeks=5)

    def test_weeks_too_high_rejects(self):
        with pytest.raises(Exception, match="total_weeks"):
            WizardPlanConfig(total_weeks=31)

    def test_weeks_zero_rejects(self):
        with pytest.raises(Exception, match="total_weeks"):
            WizardPlanConfig(total_weeks=0)

    def test_boundary_weeks_6_accepted(self):
        c = WizardPlanConfig(total_weeks=6)
        assert c.total_weeks == 6

    def test_boundary_weeks_30_accepted(self):
        c = WizardPlanConfig(total_weeks=30)
        assert c.total_weeks == 30


# ===========================================================================
# Marathon-Specific Template Tests
# ===========================================================================


class TestMarathonRaceDistance:
    """Race day workout must use the actual event distance, not volume-derived."""

    def test_race_day_distance_is_42195(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
        )
        # Race week is the last week
        race_week = plan[-1]
        assert race_week["status"] == "race"
        # Find the Race workout on Sunday
        race_workouts = [
            w for w in race_week["days"]["Sun"]["workouts"] if w["format"] == "Race"
        ]
        assert len(race_workouts) == 1, "Expected exactly one Race workout on Sunday"
        assert race_workouts[0]["distance_m"] == 42195

    def test_half_marathon_race_distance_is_21097(self):
        template = RUNNING_TEMPLATES[("half_marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="half_marathon",
        )
        race_week = plan[-1]
        race_workouts = [
            w for w in race_week["days"]["Sun"]["workouts"] if w["format"] == "Race"
        ]
        assert len(race_workouts) == 1
        # Half marathon is 21097m (as defined in EVENT_DISTANCES_M)
        assert race_workouts[0]["distance_m"] == 21097


class TestLongRunOnSunday:
    """Long runs (SLR) must land on Sunday (day index 6)."""

    def test_slr_is_on_sunday(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        for week in plan:
            sun_workouts = week["days"]["Sun"]["workouts"]
            for workout in sun_workouts:
                if "SLR" in workout["name"]:
                    # Confirm it's on Sunday by checking the date is indeed a Sunday
                    sun_date = date.fromisoformat(week["days"]["Sun"]["date"])
                    assert sun_date.weekday() == 6, (
                        f"SLR workout on {sun_date} is not a Sunday"
                    )

    def test_no_slr_on_other_days(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        other_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for week in plan:
            for day_name in other_days:
                for workout in week["days"][day_name]["workouts"]:
                    assert "SLR" not in workout["name"], (
                        f"SLR found on {day_name} in week {week['weekStarting']}"
                    )


class TestMarathonTaper:
    """Marathon plans must have a proper multi-week taper phase."""

    def test_taper_phase_exists(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        phases = calculate_phase_structure(
            14, template.phases, template.phase_proportions
        )
        taper_phases = [p for p in phases if p["name"] == "taper"]
        assert len(taper_phases) == 1
        assert taper_phases[0]["weeks"] >= 2, (
            "Marathon taper should be at least 2 weeks"
        )

    def test_taper_volume_decreases(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        # Find taper weeks (status == "taper")
        taper_weeks = [w for w in plan if w["status"] == "taper"]
        assert len(taper_weeks) >= 2

        # Volume should decrease across taper weeks
        taper_volumes = []
        for week in taper_weeks:
            vol = sum(
                w["distance_m"]
                for day in week["days"].values()
                for w in day["workouts"]
            )
            taper_volumes.append(vol)
        for i in range(len(taper_volumes) - 1):
            assert taper_volumes[i] > taper_volumes[i + 1], (
                f"Taper volume should decrease: week {i} ({taper_volumes[i]}m) "
                f"vs week {i + 1} ({taper_volumes[i + 1]}m)"
            )

    def test_early_taper_has_long_run(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        taper_weeks = [w for w in plan if w["status"] == "taper"]
        assert len(taper_weeks) >= 2
        # First taper week should have an SLR on Sunday
        first_taper_sun = taper_weeks[0]["days"]["Sun"]["workouts"]
        slr_workouts = [w for w in first_taper_sun if "SLR" in w["name"]]
        assert len(slr_workouts) == 1, (
            "First taper week should still have a long run (SLR) on Sunday"
        )

    def test_late_taper_no_long_run(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
        )
        taper_weeks = [w for w in plan if w["status"] == "taper"]
        assert len(taper_weeks) >= 2
        # Last taper week should NOT have an SLR
        last_taper_sun = taper_weeks[-1]["days"]["Sun"]["workouts"]
        slr_workouts = [w for w in last_taper_sun if "SLR" in w["name"]]
        assert len(slr_workouts) == 0, "Final taper week should not have a long run"


class TestPastStartDateValidation:
    """Plans with start dates in the past must be rejected."""

    def test_generate_rejects_past_start_date(self, session, user):
        service = PlanBuilderService(session)
        # Set event_date to 4 weeks from now but request 30 weeks -- start would
        # be ~26 weeks in the past
        wizard = _make_wizard_input(
            total_weeks=30,
            event_date=date.today() + timedelta(weeks=4),
        )
        with pytest.raises(ValueError, match="in the past"):
            service.generate_plan(wizard, user)

    def test_preview_rejects_past_start_date(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(
            total_weeks=30,
            event_date=date.today() + timedelta(weeks=4),
        )
        with pytest.raises(ValueError, match="in the past"):
            service.generate_preview(wizard)

    def test_generate_allows_future_start_date(self, session, user):
        service = PlanBuilderService(session)
        # Event 20 weeks out with 14 week plan -- start is ~6 weeks from now
        wizard = _make_wizard_input(
            total_weeks=14,
            event_date=date.today() + timedelta(weeks=20),
        )
        plan = service.generate_plan(wizard, user)
        assert plan.id is not None

    def test_generate_allows_no_event_date(self, session, user):
        service = PlanBuilderService(session)
        wizard = _make_wizard_input(total_weeks=14, event_date=None)
        plan = service.generate_plan(wizard, user)
        assert plan.id is not None


# ===========================================================================
# Taper Weeks Override Tests
# ===========================================================================


class TestTaperWeeksValidation:
    def test_taper_weeks_none_accepted(self):
        c = WizardPlanConfig(total_weeks=14, taper_weeks=None)
        assert c.taper_weeks is None

    def test_taper_weeks_1_accepted(self):
        c = WizardPlanConfig(total_weeks=14, taper_weeks=1)
        assert c.taper_weeks == 1

    def test_taper_weeks_2_accepted(self):
        c = WizardPlanConfig(total_weeks=14, taper_weeks=2)
        assert c.taper_weeks == 2

    def test_taper_weeks_3_accepted(self):
        c = WizardPlanConfig(total_weeks=14, taper_weeks=3)
        assert c.taper_weeks == 3

    def test_taper_weeks_0_rejects(self):
        with pytest.raises(Exception, match="taper_weeks"):
            WizardPlanConfig(total_weeks=14, taper_weeks=0)

    def test_taper_weeks_4_rejects(self):
        with pytest.raises(Exception, match="taper_weeks"):
            WizardPlanConfig(total_weeks=14, taper_weeks=4)

    def test_taper_weeks_negative_rejects(self):
        with pytest.raises(Exception, match="taper_weeks"):
            WizardPlanConfig(total_weeks=14, taper_weeks=-1)


class TestTaperWeeksOverride:
    """Verify that taper_weeks_override adjusts the generated plan."""

    def test_taper_override_1_week(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            taper_weeks_override=1,
        )
        taper_weeks = [w for w in plan if w["status"] == "taper"]
        assert len(taper_weeks) == 1

    def test_taper_override_3_weeks(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=16,
            sessions_per_week=5,
            event_type="marathon",
            taper_weeks_override=3,
        )
        taper_weeks = [w for w in plan if w["status"] == "taper"]
        assert len(taper_weeks) == 3

    def test_taper_override_preserves_total_weeks(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        for override in [1, 2, 3]:
            plan = generate_plan_from_template(
                template=template,
                start_date=date(2026, 3, 2),
                total_weeks=14,
                sessions_per_week=5,
                event_type="marathon",
                taper_weeks_override=override,
            )
            assert len(plan) == 14

    def test_taper_override_none_uses_default(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan_default = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            taper_weeks_override=None,
        )
        taper_default = len([w for w in plan_default if w["status"] == "taper"])
        # Default taper should be >= 2 for marathon
        assert taper_default >= 2


# ===========================================================================
# Preferred Time of Day Tests
# ===========================================================================


class TestPreferredTimeOfDayValidation:
    def test_am_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_time_of_day="AM",
        )
        assert p.preferred_time_of_day == "AM"

    def test_pm_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_time_of_day="PM",
        )
        assert p.preferred_time_of_day == "PM"

    def test_none_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_time_of_day=None,
        )
        assert p.preferred_time_of_day is None

    def test_morning_rejects(self):
        with pytest.raises(Exception, match="preferred_time_of_day"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_time_of_day="morning",
            )

    def test_lowercase_am_rejects(self):
        with pytest.raises(Exception, match="preferred_time_of_day"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_time_of_day="am",
            )


class TestPreferredTimeOfDayGeneration:
    """Verify that preferred_time_of_day overrides workout timeOfDay."""

    def test_pm_override_sets_all_workouts(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_time_of_day="PM",
        )
        for week in plan:
            for day_data in week["days"].values():
                for workout in day_data["workouts"]:
                    assert workout["timeOfDay"] == "PM", (
                        f"Expected PM but got {workout['timeOfDay']} "
                        f"for {workout['name']} in week {week['weekStarting']}"
                    )

    def test_am_override_sets_all_workouts(self):
        template = RUNNING_TEMPLATES[("10k", "beginner")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=8,
            sessions_per_week=3,
            event_type="10k",
            preferred_time_of_day="AM",
        )
        for week in plan:
            for day_data in week["days"].values():
                for workout in day_data["workouts"]:
                    assert workout["timeOfDay"] == "AM"

    def test_none_uses_template_default(self):
        template = RUNNING_TEMPLATES[("marathon", "intermediate")]
        plan = generate_plan_from_template(
            template=template,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_time_of_day=None,
        )
        # All SessionTemplates default to AM, so all should be AM
        for week in plan:
            for day_data in week["days"].values():
                for workout in day_data["workouts"]:
                    assert workout["timeOfDay"] == "AM"


# ---------------------------------------------------------------------------
# Enhancement A: Session type verification by experience level
# ---------------------------------------------------------------------------


def _phase_week_ranges(template, total_weeks):
    """Return a dict mapping phase name to (start_idx, end_idx) in the plan."""
    phases = calculate_phase_structure(
        total_weeks, template.phases, template.phase_proportions
    )
    ranges = {}
    offset = 0
    for phase in phases:
        ranges[phase["name"]] = (offset, offset + phase["weeks"])
        offset += phase["weeks"]
    return ranges


def _collect_workout_formats_for_phase(plan, template, total_weeks, phase_name):
    """Collect all workout format values from weeks of a given phase."""
    ranges = _phase_week_ranges(template, total_weeks)
    start, end = ranges[phase_name]
    formats = set()
    for week in plan[start:end]:
        for day_data in week["days"].values():
            for workout in day_data["workouts"]:
                formats.add(workout["format"])
    return formats


def _collect_workout_names_for_phase(plan, template, total_weeks, phase_name):
    """Collect all workout names from weeks of a given phase."""
    ranges = _phase_week_ranges(template, total_weeks)
    start, end = ranges[phase_name]
    names = []
    for week in plan[start:end]:
        for day_data in week["days"].values():
            for workout in day_data["workouts"]:
                names.append(workout["name"])
    return names


class TestAdvancedMarathonSessions:
    """Advanced marathon plans should have intervals + threshold + progression SLR."""

    TEMPLATE = RUNNING_TEMPLATES[("marathon", "advanced")]
    TOTAL_WEEKS = 14

    @pytest.fixture()
    def plan(self):
        return generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=self.TOTAL_WEEKS,
            sessions_per_week=6,
            event_type="marathon",
        )

    def test_build_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Intervals" in formats

    def test_build_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Threshold" in formats

    def test_build_has_progression_slr(self, plan):
        names = _collect_workout_names_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert any("Progression SLR" in n for n in names), (
            "Advanced build should have Progression SLR"
        )

    def test_build_no_tempo(self, plan):
        """Advanced build replaces tempo with intervals -- no tempo in build."""
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Tempo" not in formats

    def test_peak_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Intervals" in formats

    def test_peak_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Threshold" in formats

    def test_peak_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Tempo" in formats

    def test_peak_has_progression_slr(self, plan):
        names = _collect_workout_names_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert any("Progression SLR" in n for n in names), (
            "Advanced peak should have Progression SLR"
        )

    def test_peak_volume_is_130km(self):
        assert self.TEMPLATE.peak_volume_m == 130000


class TestIntermediateMarathonSessions:
    """Intermediate marathon: tempo + threshold in build, intervals + tempo in peak."""

    TEMPLATE = RUNNING_TEMPLATES[("marathon", "intermediate")]
    TOTAL_WEEKS = 14

    @pytest.fixture()
    def plan(self):
        return generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=self.TOTAL_WEEKS,
            sessions_per_week=6,
            event_type="marathon",
        )

    def test_build_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Tempo" in formats

    def test_build_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Threshold" in formats

    def test_build_no_intervals(self, plan):
        """Intermediate build does not have intervals (that is peak phase)."""
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Intervals" not in formats

    def test_build_has_regular_slr(self, plan):
        """Intermediate build has regular SLR, not progression."""
        names = _collect_workout_names_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        has_long = any("SLR" in n and "Progression" not in n for n in names)
        has_progression = any("Progression SLR" in n for n in names)
        assert has_long, "Intermediate build should have regular SLR"
        assert not has_progression, "Intermediate build should NOT have Progression SLR"

    def test_peak_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Intervals" in formats

    def test_peak_has_progression_slr(self, plan):
        names = _collect_workout_names_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert any("Progression SLR" in n for n in names), (
            "Intermediate peak should have Progression SLR"
        )

    def test_peak_volume_is_85km(self):
        assert self.TEMPLATE.peak_volume_m == 85000


class TestBeginnerMarathonSessions:
    """Beginner marathon: fartlek only in build, tempo only in peak, no threshold/intervals."""

    TEMPLATE = RUNNING_TEMPLATES[("marathon", "beginner")]
    TOTAL_WEEKS = 14

    @pytest.fixture()
    def plan(self):
        return generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=self.TOTAL_WEEKS,
            sessions_per_week=4,
            event_type="marathon",
        )

    def test_build_has_fartlek(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Fartlek" in formats

    def test_build_no_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Threshold" not in formats

    def test_build_no_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Intervals" not in formats

    def test_peak_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Tempo" in formats

    def test_peak_no_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Intervals" not in formats

    def test_peak_no_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Threshold" not in formats

    def test_peak_volume_is_50km(self):
        assert self.TEMPLATE.peak_volume_m == 50000


class TestAdvanced5kSessions:
    """Advanced 5K plans should have intervals + threshold in both build and peak."""

    TEMPLATE = RUNNING_TEMPLATES[("5k", "advanced")]
    TOTAL_WEEKS = 14

    @pytest.fixture()
    def plan(self):
        return generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=self.TOTAL_WEEKS,
            sessions_per_week=6,
            event_type="5k",
        )

    def test_build_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Intervals" in formats

    def test_build_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Threshold" in formats

    def test_build_has_progression_slr(self, plan):
        names = _collect_workout_names_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert any("Progression SLR" in n for n in names), (
            "Advanced 5K build should have Progression SLR"
        )

    def test_peak_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Intervals" in formats

    def test_peak_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Threshold" in formats

    def test_peak_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Tempo" in formats

    def test_peak_has_steady_run(self, plan):
        """Advanced 5K peak should have steady run on Sunday (not progression SLR)."""
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Steady" in formats

    def test_peak_volume_is_50km(self):
        assert self.TEMPLATE.peak_volume_m == 50000


class TestAdvancedTemplatesDistinct:
    """Every running event with an advanced template should be a distinct object."""

    @pytest.mark.parametrize(
        "event",
        [
            "5k",
            "10k",
            "half_marathon",
            "marathon",
        ],
    )
    def test_advanced_not_same_as_intermediate(self, event):
        adv = RUNNING_TEMPLATES[(event, "advanced")]
        inter = RUNNING_TEMPLATES[(event, "intermediate")]
        assert adv is not inter, (
            f"{event} advanced template should be distinct from intermediate"
        )

    def test_ultra_advanced_not_same_as_intermediate(self):
        adv = RUNNING_TEMPLATES[("ultra", "advanced")]
        inter = RUNNING_TEMPLATES[("ultra", "intermediate")]
        assert adv is not inter

    @pytest.mark.parametrize(
        "event",
        [
            "5k",
            "10k",
            "half_marathon",
            "marathon",
            "ultra",
        ],
    )
    def test_all_events_have_advanced(self, event):
        """Every running event should have an advanced entry in the registry."""
        assert (event, "advanced") in RUNNING_TEMPLATES


class TestAdvancedSwimmingTemplatesDistinct:
    """Every swimming event's advanced template should be a distinct object from intermediate."""

    @pytest.mark.parametrize(
        "event",
        [
            "pool_400m",
            "pool_800m",
            "pool_1500m",
        ],
    )
    def test_pool_advanced_not_same_as_intermediate(self, event):
        adv = SWIMMING_TEMPLATES[(event, "advanced")]
        inter = SWIMMING_TEMPLATES[(event, "intermediate")]
        assert adv is not inter, (
            f"{event} advanced template should be distinct from intermediate"
        )

    @pytest.mark.parametrize(
        "event",
        [
            "ow_1km",
            "ow_2.5km",
            "ow_5km",
            "ow_10km",
        ],
    )
    def test_ow_advanced_not_same_as_intermediate(self, event):
        adv = SWIMMING_TEMPLATES[(event, "advanced")]
        inter = SWIMMING_TEMPLATES[(event, "intermediate")]
        assert adv is not inter, (
            f"{event} advanced template should be distinct from intermediate"
        )

    @pytest.mark.parametrize(
        "event",
        [
            "pool_400m",
            "pool_800m",
            "pool_1500m",
            "ow_1km",
            "ow_2.5km",
            "ow_5km",
            "ow_10km",
        ],
    )
    def test_all_swimming_events_have_advanced(self, event):
        """Every swimming event should have an advanced entry in the registry."""
        assert (event, "advanced") in SWIMMING_TEMPLATES

    def test_pool_advanced_higher_volume_than_intermediate(self):
        adv = SWIMMING_TEMPLATES[("pool_1500m", "advanced")]
        inter = SWIMMING_TEMPLATES[("pool_1500m", "intermediate")]
        assert adv.peak_volume_m > inter.peak_volume_m

    def test_ow_advanced_higher_volume_than_intermediate(self):
        adv = SWIMMING_TEMPLATES[("ow_5km", "advanced")]
        inter = SWIMMING_TEMPLATES[("ow_5km", "intermediate")]
        assert adv.peak_volume_m > inter.peak_volume_m

    def test_pool_advanced_level_is_advanced(self):
        adv = SWIMMING_TEMPLATES[("pool_1500m", "advanced")]
        assert adv.level == "advanced"

    def test_ow_advanced_level_is_advanced(self):
        adv = SWIMMING_TEMPLATES[("ow_5km", "advanced")]
        assert adv.level == "advanced"


class TestAdvancedPoolSwimmingSessions:
    """Advanced pool plans should have intervals + threshold + tempo in build/peak."""

    TEMPLATE = SWIMMING_TEMPLATES[("pool_1500m", "advanced")]
    TOTAL_WEEKS = 14

    @pytest.fixture()
    def plan(self):
        return generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=self.TOTAL_WEEKS,
            sessions_per_week=6,
        )

    def test_build_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Intervals" in formats

    def test_build_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Threshold" in formats

    def test_build_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Tempo" in formats

    def test_peak_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Intervals" in formats

    def test_peak_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Threshold" in formats

    def test_peak_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Tempo" in formats

    def test_peak_volume_is_22km(self):
        assert self.TEMPLATE.peak_volume_m == 22000

    def test_generates_valid_plan(self, plan):
        assert len(plan) == self.TOTAL_WEEKS
        has_workouts = any(
            day["workouts"] for week in plan for day in week["days"].values()
        )
        assert has_workouts


class TestAdvancedOWSwimmingSessions:
    """Advanced open water plans should have intervals + threshold + OW skills."""

    TEMPLATE = SWIMMING_TEMPLATES[("ow_5km", "advanced")]
    TOTAL_WEEKS = 14

    @pytest.fixture()
    def plan(self):
        return generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=self.TOTAL_WEEKS,
            sessions_per_week=6,
        )

    def test_build_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Intervals" in formats

    def test_build_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Threshold" in formats

    def test_build_has_tempo(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert "Tempo" in formats

    def test_build_has_ow_skills(self, plan):
        """Advanced OW build should include open water skills sessions."""
        names = _collect_workout_names_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "build"
        )
        assert any("Open Water" in n for n in names), (
            "Advanced OW build should have open water sessions"
        )

    def test_peak_has_intervals(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Intervals" in formats

    def test_peak_has_threshold(self, plan):
        formats = _collect_workout_formats_for_phase(
            plan, self.TEMPLATE, self.TOTAL_WEEKS, "peak"
        )
        assert "Threshold" in formats

    def test_peak_volume_is_28km(self):
        assert self.TEMPLATE.peak_volume_m == 28000

    def test_generates_valid_plan(self, plan):
        assert len(plan) == self.TOTAL_WEEKS
        has_workouts = any(
            day["workouts"] for week in plan for day in week["days"].values()
        )
        assert has_workouts


# ===========================================================================
# Preferred Training Days Tests
# ===========================================================================


class TestPreferredTrainingDaysValidation:
    """Schema validation for preferred_training_days and preferred_long_run_day."""

    def test_valid_training_days(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_training_days=[0, 1, 2, 3, 4],
        )
        assert p.preferred_training_days == [0, 1, 2, 3, 4]

    def test_none_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_training_days=None,
        )
        assert p.preferred_training_days is None

    def test_single_day_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_training_days=[6],
        )
        assert p.preferred_training_days == [6]

    def test_all_seven_days_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_training_days=[0, 1, 2, 3, 4, 5, 6],
        )
        assert len(p.preferred_training_days) == 7

    def test_empty_list_rejects(self):
        with pytest.raises(Exception, match="preferred_training_days"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_training_days=[],
            )

    def test_duplicate_days_rejects(self):
        with pytest.raises(Exception, match="preferred_training_days"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_training_days=[0, 1, 1],
            )

    def test_out_of_range_day_rejects(self):
        with pytest.raises(Exception, match="training day"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_training_days=[0, 7],
            )

    def test_negative_day_rejects(self):
        with pytest.raises(Exception, match="training day"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_training_days=[-1, 0],
            )

    def test_valid_long_run_day(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_long_run_day=6,
        )
        assert p.preferred_long_run_day == 6

    def test_long_run_day_none_accepted(self):
        p = WizardAthleteProfile(
            experience_level="intermediate",
            age=30,
            weight_kg=70.0,
            preferred_long_run_day=None,
        )
        assert p.preferred_long_run_day is None

    def test_long_run_day_out_of_range_rejects(self):
        with pytest.raises(Exception, match="preferred_long_run_day"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_long_run_day=7,
            )

    def test_long_run_day_negative_rejects(self):
        with pytest.raises(Exception, match="preferred_long_run_day"):
            WizardAthleteProfile(
                experience_level="intermediate",
                age=30,
                weight_kg=70.0,
                preferred_long_run_day=-1,
            )


class TestPreferredTrainingDaysRemapping:
    """Verify that preferred_training_days remaps workouts to the right days."""

    TEMPLATE = RUNNING_TEMPLATES[("marathon", "intermediate")]

    def _day_indices_with_workouts(self, week):
        """Return sorted list of day indices (0=Mon..6=Sun) that have workouts."""
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        indices = []
        for i, day_name in enumerate(day_names):
            if week["days"][day_name]["workouts"]:
                indices.append(i)
        return sorted(indices)

    def test_no_preference_uses_template_days(self):
        """Without preferences, sessions land on template-defined days."""
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=None,
            preferred_long_run_day=None,
        )
        # First week should have workouts -- just verify it runs
        total_workouts = sum(len(d["workouts"]) for d in plan[0]["days"].values())
        assert total_workouts > 0

    def test_sessions_placed_on_preferred_days(self):
        """All sessions should land on user-specified training days."""
        preferred = [0, 2, 4, 5, 6]  # Mon, Wed, Fri, Sat, Sun
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=preferred,
            preferred_long_run_day=6,
        )
        for week in plan:
            active_days = self._day_indices_with_workouts(week)
            for day_idx in active_days:
                assert day_idx in preferred, (
                    f"Workout on day {day_idx} but preferred days are {preferred} "
                    f"in week {week['weekStarting']}"
                )

    def test_long_run_on_preferred_day(self):
        """Long run should land on the preferred_long_run_day."""
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=[0, 1, 3, 4, 5],
            preferred_long_run_day=5,  # Saturday
        )
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for week in plan:
            for i, day_name in enumerate(day_names):
                for workout in week["days"][day_name]["workouts"]:
                    if "SLR" in workout["name"]:
                        assert i == 5, (
                            f"SLR should be on Saturday (5) but found on "
                            f"{day_name} ({i}) in week {week['weekStarting']}"
                        )

    def test_long_run_day_only_override(self):
        """Setting only preferred_long_run_day (no preferred_training_days)
        should move the long run but keep other sessions on original days."""
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=None,
            preferred_long_run_day=5,  # Saturday instead of default Sunday
        )
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for week in plan:
            for i, day_name in enumerate(day_names):
                for workout in week["days"][day_name]["workouts"]:
                    if "SLR" in workout["name"]:
                        assert i == 5, (
                            f"SLR should be on Saturday (5) but found on "
                            f"{day_name} ({i})"
                        )

    def test_long_run_day_excluded_from_other_sessions(self):
        """No non-long-run session should be placed on the long run day."""
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=[0, 1, 2, 3, 6],
            preferred_long_run_day=6,  # Sunday
        )
        for week in plan:
            sun_workouts = week["days"]["Sun"]["workouts"]
            for w in sun_workouts:
                # Only long run formats should appear on Sunday
                assert w["format"] in ("Long", "Progression", "Race"), (
                    f"Non-long-run workout '{w['name']}' (format={w['format']}) "
                    f"found on Sunday in week {week['weekStarting']}"
                )

    def test_fewer_preferred_days_than_sessions_drops_extras(self):
        """If preferred_training_days has fewer slots than sessions_per_week,
        excess sessions are dropped."""
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=[0, 2, 6],  # Only 3 slots (1 for LR)
            preferred_long_run_day=6,
        )
        for week in plan:
            total_workouts = sum(len(d["workouts"]) for d in week["days"].values())
            # Should have at most 3 workouts (2 non-LR slots + 1 LR)
            assert total_workouts <= 3, (
                f"Expected at most 3 workouts but got {total_workouts} "
                f"in week {week['weekStarting']}"
            )

    def test_remapping_preserves_workout_count_when_enough_days(self):
        """When preferred days >= sessions, workout count is unchanged."""
        plan_default = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
        )
        plan_remapped = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=[0, 1, 2, 3, 6],
            preferred_long_run_day=6,
        )
        for default_week, remapped_week in zip(plan_default, plan_remapped):
            default_count = sum(
                len(d["workouts"]) for d in default_week["days"].values()
            )
            remapped_count = sum(
                len(d["workouts"]) for d in remapped_week["days"].values()
            )
            assert remapped_count == default_count, (
                f"Week {default_week['weekStarting']}: expected {default_count} "
                f"workouts, got {remapped_count}"
            )

    def test_move_long_run_to_monday(self):
        """Edge case: long run on Monday should work."""
        plan = generate_plan_from_template(
            template=self.TEMPLATE,
            start_date=date(2026, 3, 2),
            total_weeks=14,
            sessions_per_week=5,
            event_type="marathon",
            preferred_training_days=[0, 1, 2, 3, 4],
            preferred_long_run_day=0,  # Monday
        )
        for week in plan:
            mon_workouts = week["days"]["Mon"]["workouts"]
            long_run_formats = {"Long", "Progression"}
            has_lr = any(w["format"] in long_run_formats for w in mon_workouts)
            # In non-taper/race weeks with a long run template, LR should be on Mon
            sun_workouts = week["days"]["Sun"]["workouts"]
            sun_lr = any(w["format"] in long_run_formats for w in sun_workouts)
            # LR should not be on Sunday anymore
            if has_lr or sun_lr:
                assert not sun_lr, (
                    f"Long run should be on Monday, not Sunday, "
                    f"in week {week['weekStarting']}"
                )
