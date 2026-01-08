from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
import json

@dataclass
class Workout:
    name: str
    type: str
    distance_m: float
    timeOfDay: str = "AM"

    @staticmethod
    def from_dict(data: dict):
        return Workout(
            name=data.get("name", ""),
            type=data.get("type", "rest"),
            distance_m=float(data.get("distance_m", 0)),
            timeOfDay=data.get("timeOfDay", "AM")
        )

@dataclass
class Day:
    date: str
    workouts: List[Workout] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        return Day(
            date=data.get("date", ""),
            workouts=[Workout.from_dict(w) for w in data.get("workouts", [])]
        )

@dataclass
class Week:
    weekStarting: str
    days: Dict[str, Day] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: dict):
        days_map = {}
        for day_name, day_data in data.get("days", {}).items():
            days_map[day_name] = Day.from_dict(day_data)
        return Week(
            weekStarting=data.get("weekStarting", ""),
            days=days_map
        )

def load_plan(path: str = "plan.json") -> List[Week]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return [Week.from_dict(w) for w in data]
    except FileNotFoundError:
        return []

def load_actuals(path: str = "actuals.json") -> List['ActualActivity']:
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return [ActualActivity(**a) for a in data]
    except FileNotFoundError:
        return []

@dataclass
class ActualActivity:
    date: str
    name: str
    type: str # running, cycling, etc.
    distance_m: float
    duration_s: float
    average_pace_m_s: float
    average_hr: Optional[float] = None
    max_hr: Optional[float] = None
    average_power: Optional[float] = None
    aerobic_te: Optional[float] = None
    anaerobic_te: Optional[float] = None
    training_load: Optional[float] = None
    calories: Optional[float] = None
    activityId: Optional[int] = None
    hr_zones: List[Dict] = field(default_factory=list)
    power_zones: List[Dict] = field(default_factory=list)
    pace_zones: List[Dict] = field(default_factory=list)

@dataclass
class WeightEntry:
    date: str
    weight: float

@dataclass
class RunnerContext:
    current_weight: float
    target_weight: float
    weight_history: List[WeightEntry] = field(default_factory=list)
