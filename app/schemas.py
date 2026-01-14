from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional

class WorkoutSchema(BaseModel):
    name: str = ""
    type: str = "rest"
    distance_m: float = 0.0
    timeOfDay: str = "AM"

    model_config = ConfigDict(populate_by_name=True)

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

class RunnerContext(BaseModel):
    age: int
    gender: str
    height_cm: int
    weight_kg: WeightContext

    model_config = ConfigDict(from_attributes=True)

class ContextSchema(BaseModel):
    project: ProjectContext
    runner: RunnerContext

# Actuals (simplified for now as it has many fields)
class HrZone(BaseModel):
    zoneNumber: int
    secsInZone: float
    zoneLow: float
    zoneHigh: float
    percentInZone: float

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
