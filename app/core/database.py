from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session, Relationship
from datetime import datetime
import os

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

# Environment variables
sqlite_file_name = os.getenv("SQLITE_DB_PATH", "data/database.db")
database_url = os.getenv("DATABASE_URL")

if database_url:
    # Use the provided DATABASE_URL (e.g., for Postgres)
    engine = create_engine(database_url, echo=True)
else:
    # Fallback to SQLite
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
