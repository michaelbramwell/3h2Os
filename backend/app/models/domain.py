from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from enum import Enum
import json


class PlanType(str, Enum):
    RUNNING = "running"
    SWIMMING = "swimming"


class ActivityType(str, Enum):
    RUN = "Run"
    EASY = "Easy"
    LONG = "Long"
    WORKOUT = "Workout"
    RACE = "Race"
    REST = "Rest"
    CROSS = "Cross"
    STEADY = "Steady"
    WARMUP = "WarmUp"
    COOLDOWN = "CoolDown"
    INTERVALS = "Intervals"
    TRAIL = "Trail"
    TEMPO = "Tempo"
    PLR = "PLR"
    HILLS = "Hills"
    THRESHOLD = "Threshold"
    CYCLING = "Cycling"
    SWIMMING = "Swimming"


class GarminActivityType(str, Enum):
    RUNNING = "running"
    TRAIL_RUNNING = "trail_running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    OTHER = "other"


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
            timeOfDay=data.get("timeOfDay", "AM"),
        )


@dataclass
class Day:
    date: str
    workouts: List[Workout] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        return Day(
            date=data.get("date", ""),
            workouts=[Workout.from_dict(w) for w in data.get("workouts", [])],
        )


@dataclass
class Week:
    weekStarting: str
    days: Dict[str, Day] = field(default_factory=dict)
    status: str = "normal"  # normal, rest, taper, recovery
    id: Optional[int] = None

    @staticmethod
    def from_dict(data: dict):
        days_map = {}
        for day_name, day_data in data.get("days", {}).items():
            days_map[day_name] = Day.from_dict(day_data)
        return Week(
            weekStarting=data.get("weekStarting", ""),
            days=days_map,
            status=data.get("status", "normal"),
            id=data.get("id"),
        )


@dataclass
class ActualActivity:
    date: str
    name: str
    type: str  # running, cycling, etc.
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
    splits: List[Dict] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict):
        # Handle optional fields with defaults
        return ActualActivity(
            date=data.get("date", ""),
            name=data.get("name", ""),
            type=data.get("type", "running"),
            distance_m=float(data.get("distance_m", 0)),
            duration_s=float(data.get("duration_s", 0)),
            average_pace_m_s=float(data.get("average_pace_m_s", 0)),
            average_hr=data.get("average_hr"),
            max_hr=data.get("max_hr"),
            average_power=data.get("average_power"),
            aerobic_te=data.get("aerobic_te"),
            anaerobic_te=data.get("anaerobic_te"),
            training_load=data.get("training_load"),
            calories=data.get("calories"),
            activityId=data.get("activityId"),
            hr_zones=data.get("hr_zones", []),
            power_zones=data.get("power_zones", []),
            pace_zones=data.get("pace_zones", []),
            splits=data.get("splits", []),
        )


@dataclass
class WeightEntry:
    date: str
    weight: float


@dataclass
class RunnerContext:
    current_weight: float
    target_weight: float
    weight_history: List[WeightEntry] = field(default_factory=list)


# --- Loaders ---


def load_plan(path: str = "data/plan.json") -> List[Week]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return [Week.from_dict(w) for w in data]
    except FileNotFoundError:
        return []


def load_actuals(path: str = "data/actuals.json") -> List[ActualActivity]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return [ActualActivity.from_dict(a) for a in data]
    except FileNotFoundError:
        return []
