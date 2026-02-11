from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from enum import Enum
import json


class PlanType(str, Enum):
    RUNNING = "running"
    SWIMMING = "swimming"


class ExperienceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EventType(str, Enum):
    # Running
    FIVE_K = "5k"
    TEN_K = "10k"
    HALF_MARATHON = "half_marathon"
    MARATHON = "marathon"
    ULTRA = "ultra"
    # Swimming - Pool
    POOL_400 = "pool_400m"
    POOL_800 = "pool_800m"
    POOL_1500 = "pool_1500m"
    # Swimming - Open Water
    OW_1K = "ow_1km"
    OW_2_5K = "ow_2.5km"
    OW_5K = "ow_5km"
    OW_10K = "ow_10km"


class SwimmingVenue(str, Enum):
    POOL = "pool"
    OPEN_WATER = "open_water"


class PrimaryGoal(str, Enum):
    FINISH = "finish"
    PB = "pb"
    TARGET_TIME = "target_time"
    CONSISTENCY = "consistency"
    ENJOYMENT = "enjoyment"


class PainPoint(str, Enum):
    CRAMPING = "cramping"
    BONKING = "bonking"
    PACING = "pacing"
    INJURY = "injury"
    MENTAL_FATIGUE = "mental_fatigue"
    RECOVERY = "recovery"
    SPEED_FINAL_THIRD = "speed_final_third"
    BREATHING = "breathing"
    OPEN_WATER_ANXIETY = "open_water_anxiety"
    STROKE_EFFICIENCY = "stroke_efficiency"


# Event type groupings for sport lookup
RUNNING_EVENTS = {
    EventType.FIVE_K,
    EventType.TEN_K,
    EventType.HALF_MARATHON,
    EventType.MARATHON,
    EventType.ULTRA,
}

SWIMMING_POOL_EVENTS = {
    EventType.POOL_400,
    EventType.POOL_800,
    EventType.POOL_1500,
}

SWIMMING_OW_EVENTS = {
    EventType.OW_1K,
    EventType.OW_2_5K,
    EventType.OW_5K,
    EventType.OW_10K,
}

SWIMMING_EVENTS = SWIMMING_POOL_EVENTS | SWIMMING_OW_EVENTS


# Event distances in metres (for template parameterisation)
EVENT_DISTANCES_M = {
    EventType.FIVE_K: 5000,
    EventType.TEN_K: 10000,
    EventType.HALF_MARATHON: 21097,
    EventType.MARATHON: 42195,
    EventType.ULTRA: 50000,
    EventType.POOL_400: 400,
    EventType.POOL_800: 800,
    EventType.POOL_1500: 1500,
    EventType.OW_1K: 1000,
    EventType.OW_2_5K: 2500,
    EventType.OW_5K: 5000,
    EventType.OW_10K: 10000,
}


class ActivityType(str, Enum):
    RUN = "Run"
    TRAIL = "Trail"
    CYCLING = "Cycling"
    SWIMMING = "Swimming"
    CROSS = "Cross"
    REST = "Rest"
    OTHER = "Other"


class WorkoutFormat(str, Enum):
    EASY = "Easy"
    LONG = "Long"
    TEMPO = "Tempo"
    THRESHOLD = "Threshold"
    INTERVALS = "Intervals"
    RACE = "Race"
    RECOVERY = "Recovery"
    TECHNIQUE = "Technique"
    HILLS = "Hills"
    FARTLEK = "Fartlek"
    PROGRESSION = "Progression"
    STEADY = "Steady"
    WARMUP = "WarmUp"
    COOLDOWN = "CoolDown"
    TIME_TRIAL = "TimeTrial"


# Centralized filter lists to avoid duplication across the codebase
SWIM_ACTIVITY_TYPES = {
    "swimming",
    "swim",
    "pool",
    "lap_swimming",
    "open_water_swimming",
}

RUN_ACTIVITY_TYPES = {
    "running",
    "run",
    "trail_running",
    "treadmill_running",
    "trail",
}


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
    format: Optional[str] = None

    @staticmethod
    def from_dict(data: dict):
        return Workout(
            name=data.get("name", ""),
            type=data.get("type", "rest"),
            distance_m=float(data.get("distance_m", 0)),
            timeOfDay=data.get("timeOfDay", "AM"),
            format=data.get("format"),
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
class RunnerContext:
    pass
    # Removed weight related fields


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
