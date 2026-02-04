from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import List, Dict, Any, Optional
from datetime import date
from app.models.domain import ActivityType, WorkoutFormat


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


class FuelingStrategy(BaseModel):
    carbsPerHr: Optional[int] = 0
    sodiumPerHr: Optional[int] = 0
    preRunCarbs: Optional[int] = 0


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
    fueling: Optional[FuelingStrategy] = None
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
