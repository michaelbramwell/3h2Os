from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Dict, Any, Optional
from datetime import date
from app.models.domain import ActivityType

class WorkoutCreate(BaseModel):
    date: date
    name: str = "New Workout"
    type: ActivityType = ActivityType.RUN
    distance_m: float = 0.0
    timeOfDay: str = "AM"
    description: Optional[str] = None

    @field_validator('distance_m')
    @classmethod
    def validate_distance(cls, v: float) -> float:
        if v < 0 or v > 1000000:  # 1000km sanity check
            raise ValueError("Distance must be between 0 and 1000km")
        return v
    
    @field_validator('timeOfDay')
    @classmethod
    def validate_time_of_day(cls, v: str) -> str:
        if v not in ["AM", "PM"]:
            raise ValueError("timeOfDay must be 'AM' or 'PM'")
        return v

class WorkoutSchema(BaseModel):
    id: Optional[int] = None
    name: str = ""
    type: ActivityType = ActivityType.REST
    distance_m: float = 0.0
    timeOfDay: str = "AM"
    description: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class WorkoutUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ActivityType] = None
    distance_m: Optional[float] = None
    description: Optional[str] = None
    timeOfDay: Optional[str] = None

    @field_validator('distance_m')
    @classmethod
    def validate_distance(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 1000000):
            raise ValueError("Distance must be between 0 and 1000km")
        return v
    
    @field_validator('timeOfDay')
    @classmethod
    def validate_time_of_day(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["AM", "PM"]:
            raise ValueError("timeOfDay must be 'AM' or 'PM'")
        return v


class DaySchema(BaseModel):
    date: str
    workouts: List[WorkoutSchema] = Field(default_factory=list)

class WeekSchema(BaseModel):
    weekStarting: str
    status: str = "normal"
    days: Dict[str, DaySchema] = Field(default_factory=dict)

class PlanCreate(BaseModel):
    title: str = "New Plan"
    weeks: List[WeekSchema]

# Response schema for update operation
class PlanUpdateResponse(BaseModel):
    status: str
    message: str
    id: int
    title: str

# Context Schemas
class ProjectContext(BaseModel):
    name: str
    goal: str
    event: str
    event_date: str = Field(alias="eventDate")
    
    @field_validator('event_date', mode='before')
    @classmethod
    def convert_date_to_str(cls, v: Any) -> str:
        if hasattr(v, 'isoformat'):
            return v.isoformat()
        return str(v)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class WeightRecord(BaseModel):
    date: str = Field(serialization_alias="date")
    weight: float = Field(serialization_alias="weight")
    
    # Allow mapping from DB fields 'date_recorded' and 'weight_kg'
    # We can use a property or just explicit mapping. 
    # Explicit mapping is often clearer for simple transformations.

class WeightContext(BaseModel):
    current: float
    target: float
    history: List[WeightRecord] = Field(default_factory=list)

class FuelingStrategy(BaseModel):
    carbsPerHr: int
    sodiumPerHr: int
    preRunCarbs: int

class TrainingZone(BaseModel):
    zone: int
    lowBoundary_m_s: float
    description: Optional[str] = None

class TrainingZones(BaseModel):
    pace: List[TrainingZone] = Field(default_factory=list)
    heartRate: List[TrainingZone] = Field(default_factory=list)

class RunnerContext(BaseModel):
    age: int
    gender: str
    height_cm: int
    weight_kg: WeightContext
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
