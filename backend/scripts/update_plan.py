import os
import sys

# Ensure we can import from app relative to this script's location
# This allows running from project root or backend/ directory
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
# Also try parent of backend_dir if app is not found
sys.path.append(backend_dir)
sys.path.append(os.path.dirname(backend_dir))

from sqlmodel import Session, select
from app.core.database import engine, User
from app.services.plans import PlanService

# Fix for DB connection when running on host
if "DATABASE_URL" not in os.environ:
    # Default to localhost Postgres if not set
    user = os.getenv("POSTGRES_USER", "user")
    password = os.getenv("POSTGRES_PASSWORD", "password")
    db = os.getenv("POSTGRES_DB", "running_db")
    os.environ["DATABASE_URL"] = (
        f"postgresql+psycopg://{user}:{password}@localhost:5432/{db}"
    )
elif "@db:" in os.environ["DATABASE_URL"]:
    # Use localhost if mapped to docker service name
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL"].replace(
        "@db:", "@localhost:"
    )


def main():
    with Session(engine) as session:
        service = PlanService(session)

        # Get default user
        username = os.getenv("DEFAULT_USERNAME", "runner")
        user = session.exec(select(User).where(User.username == username)).first()

        if not user:
            print(f"User '{username}' not found.")
            return

        print(f"Recalculating plan for user: {username}")
        service.recalculate_plan_progression(user)
        print("Plan recalculation complete.")


if __name__ == "__main__":
    main()
