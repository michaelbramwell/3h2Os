from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship
from datetime import datetime

# --- Models ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    plans: List["RunnerPlan"] = Relationship(back_populates="user")

class RunnerPlan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    is_active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Store the entire legacy plan.json structure as a JSON string for now
    # This allows us to "multi-tenant" the file structure immediately
    plan_json: str = Field(default="[]") 
    
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional[User] = Relationship(back_populates="plans")

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
