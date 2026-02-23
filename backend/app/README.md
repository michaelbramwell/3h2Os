# 3h2Os Backend API

The backend for the 3h2Os platform, built with FastAPI.

## Tech Stack
- **Framework:** FastAPI
- **Database:** PostgreSQL 15 (Production/Docker)
- **Auth:** Keycloak 26 (OIDC/JWT with RS256, JWKS)
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Migrations:** Alembic
- **Package Manager:** uv
- **Python:** 3.13

## Architecture

```
app/
  main.py                 # FastAPI app setup, lifespan, CORS, router mounting
  schemas.py              # Pydantic DTOs (WizardInput, PlanPreview, WorkoutSchema, etc.)
  models/
    domain.py             # Domain dataclasses and enums (PlanType, EventType, etc.)
  routers/
    api.py                # All API endpoints (plans, workouts, wizard, garmin, etc.)
    pages.py              # HTML page route (Jinja2 template)
  services/
    plans.py              # PlanService -- CRUD for plans/weeks/workouts, validation
    plan_builder.py       # PlanBuilderService -- wizard -> template -> plan generation
    activities.py         # ActivityService -- save/retrieve actual activities
    context.py            # ContextService -- user context (profile, project, zones)
    garmin.py             # GarminService -- Garmin Connect OAuth, activity sync
  core/
    database.py           # SQLModel tables (User, RunnerPlan, PlanWeek, PlanWorkout, etc.)
    auth.py               # JWT/Keycloak middleware with JWKS caching
    validation.py         # Training guardrails (volume, intensity, long run ratio)
    zones.py              # Zone calculator (HR, pace, swim CSS)
    mappers.py            # Bidirectional conversion between JSON and relational tables
    plan_logic.py         # Pure logic for volume calculation and progression
    services.py           # Legacy service functions (partially superseded)
    templates/
      __init__.py         # Template engine exports
      base.py             # Shared periodisation logic, volume curves, plan generation
      running.py          # 15 running plan templates (5K/10K/half/marathon/ultra x 3 levels)
      swimming.py         # 24 swimming plan templates (pool + open water x 3 levels)
scripts/                  # Automation (fetch_actuals, reflect_and_validate, sync_to_garmin)
migrations/               # Alembic database migrations
tests/                    # pytest suite (219 tests)
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `User` | Authenticated users (Keycloak sub ID) |
| `RunnerPlan` | Training plans (title, type, active flag) |
| `PlanWeek` | Weeks within a plan (week number, status, dates) |
| `PlanWorkout` | Individual workouts (day, type, distance, description) |
| `RunnerProfile` | Athlete profile (experience, zones, pain points) |
| `RunnerProject` | Event info (event type, target time, goals) |
| `ActualActivity` | Completed activities from Garmin |
| `PlanTemplate` | Plan template definitions |

## Running Locally

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run Migrations (Initial Setup):**
   ```bash
   uv run python -m db.migrate
   ```

3. **Run Server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   - API: `http://localhost:8000`
   - Docs: `http://localhost:8000/docs`
   - The API is protected by Keycloak. You need a valid JWT token to access endpoints.

4. **JWT Authentication Configuration (Local Dev):**
   The application uses RS256 for JWT signature verification. For local development without Keycloak, the app disables signature verification in dev mode (with a warning).

## Running with Docker (PostgreSQL)

```bash
# Run from the project root directory
docker compose up --build
```

This starts PostgreSQL, Keycloak, and the FastAPI app with automatic migrations.

## Migrations

```bash
# Apply pending migrations
uv run python -m db.migrate

# Check migration status
uv run python -m db.migrate --status
```

New migrations are plain SQL files in `db/migrations/`, numbered sequentially
(e.g. `003_add_foo.sql`). The runner tracks applied scripts in a
`__schema_versions` table.

## Tests

```bash
uv run pytest
```

219 tests covering plan CRUD, workout validation, template generation, zone calculation, and plan builder service.
