from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship
from datetime import datetime, date

# --- Models ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    plans: List["RunnerPlan"] = Relationship(back_populates="user")

class PlanWorkout(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    week_id: int = Field(foreign_key="planweek.id")
    date: date
    day_name: str # Mon, Tue...
    
    name: str
    description: Optional[str] = None
    activity_type: str = "Run" # Run, Rest, Cross, etc.
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
    is_active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Deprecated: Store the entire legacy plan.json structure as a JSON string
    plan_json: str = Field(default="[]") 
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="plans")
    weeks: List["PlanWeek"] = Relationship(back_populates="plan")

# --- Database Connection ---
import os

database_url = os.getenv("DATABASE_URL")

if database_url:
    # Postgres
    engine = create_engine(database_url, echo=True)
else:
    # SQLite fallback
    sqlite_file_name = os.getenv("SQLITE_DB_PATH", "data/database.db")
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    # check_same_thread=False is needed for SQLite with FastAPI
    connect_args = {"check_same_thread": False}
    engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
