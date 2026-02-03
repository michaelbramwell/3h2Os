from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship
from sqlalchemy import BigInteger, Column, String
from datetime import datetime, date
import os
from app.models.domain import ActivityType, WorkoutFormat

# --- Models ---


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    plans: List["RunnerPlan"] = Relationship(back_populates="user")
    activities: List["ActualActivity"] = Relationship(back_populates="user")
    project: Optional["RunnerProject"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )
    profile: Optional["RunnerProfile"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"uselist": False}
    )


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

    # Deprecated: Store the entire legacy plan.json structure as a JSON string
    plan_json: str = Field(default="[]")

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

    user: "User" = Relationship(back_populates="project")


class RunnerProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")

    age: int
    gender: str
    height_cm: int
    # Removed current_weight and target_weight
    # Removed weight_history relationship

    # JSON strings for complex nested data
    training_zones_json: Optional[str] = Field(default=None)
    swim_zones_json: Optional[str] = Field(default=None)
    fueling_json: Optional[str] = Field(default=None)

    user: "User" = Relationship(back_populates="profile")
    # weight_history removed


class ActualActivity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    activity_id: int = Field(
        sa_column=Column(BigInteger(), unique=True, index=True)
    )  # Garmin ID
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
