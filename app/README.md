# 3h2Os Backend API

The backend for the 3h2Os project, built with FastAPI.

## Tech Stack
- **Framework:** FastAPI
- **Database:** SQLite (Local Dev) or PostgreSQL (Production/Docker)
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Migrations:** Alembic
- **Package Manager:** uv

## Running Locally (SQLite)

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run Migrations (Initial Setup):**
   ```bash
   uv run alembic upgrade head
   ```

3. **Run Server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   - Access the API at `http://localhost:8000`.
   - API Documentation: `http://localhost:8000/docs`.

## Running with Docker (PostgreSQL)

This project includes a Docker composition that runs the API alongside a PostgreSQL database.

1. **Start Services:**
   ```bash
   docker compose up --build
   ```
   This will:
   - Start a PostgreSQL 15 container.
   - Build the FastAPI app image.
   - Automatically run migrations (`alembic upgrade head`) on startup.
   - Expose the API at `http://localhost:8000`.

2. **Environment Configuration:**
   - The app detects the `DATABASE_URL` environment variable.
   - If present, it connects to that DB (e.g. Postgres).
   - If absent, it defaults to a local SQLite file at `data/database.db`.

## Migrations

Managing database schema changes:

- **Create a new migration:**
  ```bash
  uv run alembic revision --autogenerate -m "Description of change"
  ```
- **Apply migrations:**
  ```bash
  uv run alembic upgrade head
  ```

