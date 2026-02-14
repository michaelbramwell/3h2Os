from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Dict, Any, Literal, Optional
from datetime import date
from app.models.domain import (
    ActivityType,
    WorkoutFormat,
    EventType,
    ExperienceLevel,
    PrimaryGoal,
    PainPoint,
)


# --- Wizard Schemas ---

_VALID_SPORTS = {"running", "swimming"}
_VALID_EVENT_TYPES = {e.value for e in EventType}
_VALID_EXPERIENCE_LEVELS = {e.value for e in ExperienceLevel}
_VALID_PRIMARY_GOALS = {e.value for e in PrimaryGoal}
_VALID_PAIN_POINTS = {e.value for e in PainPoint}


class WizardSportEvent(BaseModel):
    """Step 1: Sport & Event selection."""

    sport: str  # "running" | "swimming"
    event_type: str  # EventType enum value
    event_name: Optional[str] = None  # Free text, e.g. "Perth City to Surf 2026"
    event_date: Optional[date] = None

    @field_validator("sport")
    @classmethod
    def validate_sport(cls, v: str) -> str:
        if v not in _VALID_SPORTS:
            raise ValueError(f"sport must be one of {sorted(_VALID_SPORTS)}, got '{v}'")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in _VALID_EVENT_TYPES:
            raise ValueError(f"event_type must be a valid EventType value, got '{v}'")
        return v


class WizardAthleteProfile(BaseModel):
    """Step 2: Athlete profile."""

    experience_level: str  # ExperienceLevel enum value
    age: int
    weight_kg: float
    events_completed: int = 0  # For the selected event type
    preferred_time_of_day: Optional[str] = None  # "AM" or "PM", None = no preference
    preferred_training_days: Optional[List[int]] = None  # Day indices 0=Mon..6=Sun
    preferred_long_run_day: Optional[int] = None  # Day index 0=Mon..6=Sun
    use_calculated_zones: bool = True  # True = auto-calculate, False = manual entry
    custom_zones: Optional[Dict[str, Any]] = (
        None  # Only if use_calculated_zones is False
    )

    @field_validator("experience_level")
    @classmethod
    def validate_experience_level(cls, v: str) -> str:
        if v not in _VALID_EXPERIENCE_LEVELS:
            raise ValueError(
                f"experience_level must be one of {sorted(_VALID_EXPERIENCE_LEVELS)}, got '{v}'"
            )
        return v

    @field_validator("age")
    @classmethod
    def validate_age(cls, v: int) -> int:
        if v < 10 or v > 100:
            raise ValueError("age must be between 10 and 100")
        return v

    @field_validator("preferred_time_of_day")
    @classmethod
    def validate_preferred_time_of_day(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("AM", "PM"):
            raise ValueError("preferred_time_of_day must be 'AM' or 'PM'")
        return v

    @field_validator("preferred_training_days")
    @classmethod
    def validate_preferred_training_days(
        cls, v: Optional[List[int]]
    ) -> Optional[List[int]]:
        if v is not None:
            if len(v) < 1 or len(v) > 7:
                raise ValueError("preferred_training_days must have 1-7 entries")
            for day in v:
                if day < 0 or day > 6:
                    raise ValueError(
                        "Each training day must be 0 (Mon) through 6 (Sun)"
                    )
            if len(set(v)) != len(v):
                raise ValueError("preferred_training_days must not have duplicates")
        return v

    @field_validator("preferred_long_run_day")
    @classmethod
    def validate_preferred_long_run_day(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 0 or v > 6):
            raise ValueError("preferred_long_run_day must be 0 (Mon) through 6 (Sun)")
        return v


class WizardGoalsFocus(BaseModel):
    """Step 3: Goals & focus."""

    primary_goal: str  # PrimaryGoal enum value
    target_time: Optional[str] = None  # e.g. "3:45:00", only if goal is "target_time"
    pain_points: List[str] = Field(
        default_factory=list
    )  # List of PainPoint enum values
    weekly_availability: int = 5  # Days per week (1-7)
    longest_recent_distance_m: int = 0  # Current longest session in metres

    @field_validator("primary_goal")
    @classmethod
    def validate_primary_goal(cls, v: str) -> str:
        if v not in _VALID_PRIMARY_GOALS:
            raise ValueError(
                f"primary_goal must be one of {sorted(_VALID_PRIMARY_GOALS)}, got '{v}'"
            )
        return v

    @field_validator("pain_points")
    @classmethod
    def validate_pain_points(cls, v: List[str]) -> List[str]:
        for pp in v:
            if pp not in _VALID_PAIN_POINTS:
                raise ValueError(
                    f"Each pain_point must be one of {sorted(_VALID_PAIN_POINTS)}, got '{pp}'"
                )
        return v

    @field_validator("weekly_availability")
    @classmethod
    def validate_weekly_availability(cls, v: int) -> int:
        if v < 1 or v > 7:
            raise ValueError("weekly_availability must be between 1 and 7")
        return v


class WizardPlanConfig(BaseModel):
    """Step 4: Plan generation config."""

    total_weeks: int = 14
    taper_weeks: Optional[int] = None  # 1-3, None = use template default
    generation_method: Literal["template", "ai", "manual"] = "template"

    @field_validator("total_weeks")
    @classmethod
    def validate_total_weeks(cls, v: int) -> int:
        if v < 6 or v > 30:
            raise ValueError("total_weeks must be between 6 and 30")
        return v

    @field_validator("taper_weeks")
    @classmethod
    def validate_taper_weeks(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 3):
            raise ValueError("taper_weeks must be between 1 and 3")
        return v


class WizardInput(BaseModel):
    """Complete wizard submission combining all steps."""

    sport_event: WizardSportEvent
    athlete_profile: WizardAthleteProfile
    goals_focus: WizardGoalsFocus
    plan_config: WizardPlanConfig


class PhasePreview(BaseModel):
    """A single phase in the plan preview."""

    name: str  # "Base", "Build", "Peak", "Taper", "Race"
    weeks: int
    description: str


class PlanPreview(BaseModel):
    """Preview response returned before committing a plan."""

    title: str
    sport: str
    event_type: str
    total_weeks: int
    phases: List[PhasePreview]
    peak_weekly_volume_m: float
    weekly_volumes_m: List[float]  # Volume per week for chart
    sessions_per_week: int
    zones: Optional[Dict[str, Any]] = None  # Calculated or custom zones


class ClonePlanRequest(BaseModel):
    """Request to clone an existing plan."""

    new_title: str
    date_offset_days: int = 0  # Shift all dates by N days (must be a multiple of 7)

    @field_validator("date_offset_days")
    @classmethod
    def validate_date_offset_days(cls, v: int) -> int:
        if v % 7 != 0:
            raise ValueError(
                "date_offset_days must be a multiple of 7 to preserve Monday alignment"
            )
        return v


class WorkoutCreate(BaseModel):
    date: date
    name: str = "New Workout"
    type: ActivityType = ActivityType.RUN
    format: Optional[WorkoutFormat] = None
    distance_m: float = 0.0
    timeOfDay: str = "AM"
    description: Optional[str] = None

    @field_validator("distance_m")
    @classmethod
    def validate_distance(cls, v: float) -> float:
        if v < 0 or v > 1000000:  # 1000km sanity check
            raise ValueError("Distance must be between 0 and 1000km")
        return v

    @field_validator("timeOfDay")
    @classmethod
    def validate_time_of_day(cls, v: str) -> str:
        if v not in ["AM", "PM"]:
            raise ValueError("timeOfDay must be 'AM' or 'PM'")
        return v


class WorkoutSchema(BaseModel):
    id: Optional[int] = None
    name: str = ""
    type: ActivityType = ActivityType.REST
    format: Optional[WorkoutFormat] = None
    distance_m: float = 0.0
    timeOfDay: str = "AM"
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("type", mode="before")
    @classmethod
    def map_legacy_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            # Map legacy lowercase values to Enum values
            legacy_map = {
                "running": "Run",
                "run": "Run",
                "trail": "Trail",
                "trail_running": "Trail",
                "cycling": "Cycling",
                "bike": "Cycling",
                "swimming": "Swimming",
                "swim": "Swimming",
                "pool": "Swimming",
                "cross": "Cross",
                "rest": "Rest",
                # Format-types that imply Run
                "easy": "Run",
                "long": "Run",
                "tempo": "Run",
                "intervals": "Run",
                "race": "Run",
                "recovery": "Run",
                "hills": "Run",
                "steady": "Run",
                "warmup": "Run",
                "cooldown": "Run",
                "fartlek": "Run",
                "progression": "Run",
                "time_trial": "Run",
                "track": "Run",
                "plr": "Run",
                "threshold": "Run",
            }
            return legacy_map.get(v.lower(), v)
        return v

    @model_validator(mode="before")
    @classmethod
    def extract_format_from_legacy_type(cls, data: Any) -> Any:
        if isinstance(data, dict):
            raw_type = data.get("type")
            current_format = data.get("format")

            if raw_type and isinstance(raw_type, str) and not current_format:
                raw_lower = raw_type.lower()
                # Map legacy types that are actually formats
                format_map = {
                    "easy": "Easy",
                    "long": "Long",
                    "tempo": "Tempo",
                    "intervals": "Intervals",
                    "race": "Race",
                    "recovery": "Recovery",
                    "hills": "Hills",
                    "steady": "Steady",
                    "warmup": "WarmUp",
                    "cooldown": "CoolDown",
                    "fartlek": "Fartlek",
                    "progression": "Progression",
                    "time_trial": "TimeTrial",
                    "track": "Intervals",
                    "plr": "Long",
                    "threshold": "Threshold",
                }
                if raw_lower in format_map:
                    data["format"] = format_map[raw_lower]
        return data


class WorkoutUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ActivityType] = None
    format: Optional[WorkoutFormat] = None
    distance_m: Optional[float] = None
    description: Optional[str] = None
    timeOfDay: Optional[str] = None

    @field_validator("distance_m")
    @classmethod
    def validate_distance(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 1000000):
            raise ValueError("Distance must be between 0 and 1000km")
        return v

    @field_validator("timeOfDay")
    @classmethod
    def validate_time_of_day(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["AM", "PM"]:
            raise ValueError("timeOfDay must be 'AM' or 'PM'")
        return v


class DaySchema(BaseModel):
    date: str
    workouts: List[WorkoutSchema] = Field(default_factory=list)


class WeekSchema(BaseModel):
    id: Optional[int] = None
    weekStarting: str
    status: str = "normal"
    days: Dict[str, DaySchema] = Field(default_factory=dict)


class WeekUpdate(BaseModel):
    status: Optional[str] = None
    weekStarting: Optional[str] = None


class PlanCreate(BaseModel):
    title: str = "New Plan"
    type: str = "running"
    weeks: List[WeekSchema]

    @field_validator("weeks")
    @classmethod
    def validate_weeks_not_empty(cls, v: List[WeekSchema]) -> List[WeekSchema]:
        if not v:
            raise ValueError("Plan must contain at least one week")
        return v


# Response schema for update operation
class PlanUpdateResponse(BaseModel):
    status: str
    message: str
    id: int
    title: str
    type: str


# Context Schemas
class ProjectContext(BaseModel):
    name: str
    goal: str
    event: str
    event_date: str = Field(alias="eventDate")

    @field_validator("event_date", mode="before")
    @classmethod
    def convert_date_to_str(cls, v: Any) -> str:
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TrainingZone(BaseModel):
    zone: int
    lowBoundary_m_s: float
    description: Optional[str] = None


class TrainingZones(BaseModel):
    pace: List[TrainingZone] = Field(default_factory=list)
    heartRate: List[TrainingZone] = Field(default_factory=list)
    swimPace: List[TrainingZone] = Field(default_factory=list)


class RunnerContext(BaseModel):
    age: int
    gender: str
    height_cm: int
    trainingZones: Optional[TrainingZones] = None
    personalBests: Optional[Dict[str, str]] = None

    model_config = ConfigDict(from_attributes=True)


class ContextSchema(BaseModel):
    project: ProjectContext
    runner: RunnerContext


# Actuals (simplified for now as it has many fields)
class HrZone(BaseModel):
    zoneNumber: int
    secsInZone: float
    zoneLow: Optional[float] = Field(default=0.0, validation_alias="zoneLowBoundary")
    zoneHigh: Optional[float] = 0.0
    percentInZone: Optional[float] = 0.0
    avgValue: Optional[float] = 0.0

    model_config = ConfigDict(populate_by_name=True)


class ActivitySchema(BaseModel):
    date: str
    name: str
    type: str
    distance_m: float
    duration_s: float
    activityId: int
    average_pace_m_s: Optional[float] = None
    average_hr: Optional[float] = None
    max_hr: Optional[float] = None
    average_power: Optional[float] = None
    aerobic_te: Optional[float] = None
    anaerobic_te: Optional[float] = None
    training_load: Optional[float] = None
    calories: Optional[float] = None
    hr_zones: Optional[List[HrZone]] = None
    pace_zones: Optional[List[HrZone]] = None
    power_zones: Optional[List[HrZone]] = None
    splits: Optional[List[Dict[str, Any]]] = None


class GarminLogin(BaseModel):
    email: str
    password: str


class GarminToken(BaseModel):
    token: str
