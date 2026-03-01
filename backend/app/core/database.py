from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship
from sqlalchemy import BigInteger, Column, String
from datetime import datetime, date
import os
from app.models.domain import ActivityType, WorkoutFormat

# --- Models ---

# Valid user types for feature flag targeting
USER_TYPES = {"standard", "alpha", "beta", "premium"}


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # JSON array of user type strings, e.g. '["standard"]'
    user_types_json: Optional[str] = Field(default='["standard"]')

    plans: List["RunnerPlan"] = Relationship(back_populates="user")
    activities: List["ActualActivity"] = Relationship(back_populates="user")
    project: Optional["RunnerProject"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    profile: Optional["RunnerProfile"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )


class FeatureFlag(SQLModel, table=True):
    """
    A named feature flag that can be enabled for specific user types or all users.

    enabled_for_json: JSON array of user type strings that have this flag enabled,
                      or '["*"]' to mean all users, or '[]' to mean no users (off).
    Example: '["alpha", "beta"]' — only alpha and beta users see this feature.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # e.g. "isSwimmingEnabled"
    enabled_for_json: str = Field(default="[]")  # JSON array of user types or ["*"]
    description: Optional[str] = Field(default=None)


class StravaToken(SQLModel, table=True):
    """
    Stores OAuth token data for a user's Strava connection.
    One row per user; upserted on every token exchange or refresh.
    """

    __tablename__ = "strava_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    athlete_id: int  # Strava's numeric athlete ID
    access_token: str  # Short-lived; expires after ~6 hours
    refresh_token: str  # Long-lived; used to obtain a new access token
    expires_at: int  # Unix epoch seconds
    scope: str = Field(default="activity:read_all,profile:read_all")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PlanWorkout(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    week_id: int = Field(foreign_key="planweek.id")
    date: date
    day_name: str  # Mon, Tue...

    name: str
    description: Optional[str] = None
    activity_type: ActivityType = Field(default=ActivityType.RUN, sa_type=String)
    workout_format: Optional[WorkoutFormat] = Field(default=None, sa_type=String)
    distance_m: float = 0.0
    time_of_day: str = "AM"

    week: "PlanWeek" = Relationship(back_populates="workouts")


class PlanWeek(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    plan_id: int = Field(foreign_key="runnerplan.id")
    start_date: date
    status: str = "normal"

    plan: "RunnerPlan" = Relationship(back_populates="weeks")
    workouts: List["PlanWorkout"] = Relationship(back_populates="week")


class RunnerPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    type: str = Field(default="running")  # Maps to PlanType enum
    is_active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Project context snapshot – copied from RunnerProject at creation time
    # so that activate_plan can restore it when switching plans.
    event: Optional[str] = Field(default=None)
    goal: Optional[str] = Field(default=None)
    event_date: Optional[date] = Field(default=None)

    # Deprecated: Store the entire legacy plan.json structure as a JSON string
    plan_json: str = Field(default="[]")

    # Store the wizard input used to create/edit this plan so it can be recalled
    wizard_input_json: Optional[str] = Field(default=None)

    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="plans")
    weeks: List["PlanWeek"] = Relationship(back_populates="plan")


class RunnerProject(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    name: str = "My Project"
    goal: str
    event: str
    event_date: date

    # Wizard-driven fields
    event_type: Optional[str] = Field(default=None)  # EventType enum value
    target_time: Optional[str] = Field(default=None)  # e.g. "3:45:00"
    primary_goal: Optional[str] = Field(default=None)  # PrimaryGoal enum value

    user: "User" = Relationship(back_populates="project")


class RunnerProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    age: int
    gender: str
    height_cm: int

    # Date of birth — stored so age can be computed dynamically; imported from Strava/Garmin.
    birthday: Optional[date] = Field(default=None)

    # Wizard-driven fields
    weight_kg: Optional[float] = Field(default=None)
    ftp: Optional[int] = Field(
        default=None
    )  # Functional Threshold Power (watts); imported from Strava
    experience_level: Optional[str] = Field(default=None)  # ExperienceLevel enum value
    events_completed_json: Optional[str] = Field(
        default=None
    )  # JSON map e.g. {"marathon": 3}
    pain_points_json: Optional[str] = Field(
        default=None
    )  # JSON array of PainPoint values
    weekly_availability: Optional[int] = Field(default=None)  # days per week
    longest_recent_distance_m: Optional[int] = Field(default=None)

    # JSON strings for complex nested data
    training_zones_json: Optional[str] = Field(default=None)
    swim_zones_json: Optional[str] = Field(default=None)
    fueling_json: Optional[str] = Field(default=None)

    user: "User" = Relationship(back_populates="profile")


class ActualActivity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger(), unique=True, index=True, nullable=True),
    )  # Garmin activity ID; null for Strava-only records
    strava_activity_id: Optional[int] = Field(
        default=None,
        sa_column=Column(BigInteger(), unique=True, index=True, nullable=True),
    )  # Strava activity ID; null for Garmin-only records
    source: str = Field(default="garmin")  # 'garmin' | 'strava' | 'manual'
    user_id: int = Field(foreign_key="user.id")

    date: date
    name: str
    type: str  # running, cycling, etc.

    distance_m: float
    duration_s: float

    average_pace_m_s: Optional[float] = None
    average_hr: Optional[float] = None
    max_hr: Optional[float] = None
    average_power: Optional[float] = None

    aerobic_te: Optional[float] = None
    anaerobic_te: Optional[float] = None
    training_load: Optional[float] = None
    calories: Optional[float] = None

    # Store zones as JSON string for simplicity in SQLModel/SQLite
    hr_zones_json: Optional[str] = None
    pace_zones_json: Optional[str] = None
    power_zones_json: Optional[str] = None
    splits_json: Optional[str] = None

    user: "User" = Relationship(back_populates="activities")


class PlanTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sport: str  # "running" | "swimming"
    event_type: str  # EventType enum value
    level: str  # ExperienceLevel enum value
    default_weeks: int = 14
    structure_json: str  # JSON blob defining phases, session patterns, volume curve


# --- Database Connection ---

# Environment variables
# Use absolute path to ensure DB is found regardless of CWD of the runner script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sqlite_file_name = os.getenv(
    "SQLITE_DB_PATH", os.path.join(BASE_DIR, "data", "database.db")
)
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Use the provided DATABASE_URL (e.g., for Postgres)
    engine = create_engine(database_url, echo=False)
else:
    # Fallback to SQLite (Only for local dev if Postgres is missing)
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    # check_same_thread=False is needed for SQLite with FastAPI
    connect_args = {"check_same_thread": False}
    engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
