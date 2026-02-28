# Training Assistant Instructions

When working in this workspace, always refer to the following context to understand the 3h2Os training plan platform.

1.  **Architecture**: This is a **FastAPI** application using **SQLModel** (PostgreSQL) for the backend API, and a **React 19** (Vite) frontend using **TanStack Router/Query**.
2.  **Source of Truth**:
    *   **Logic**: `backend/app/` contains the API, `frontend/src/` contains the UI, `backend/scripts/` contains automation.
    *   **Data**: PostgreSQL is the **single source of truth**. Legacy JSON files have been deprecated.

### Project Structure Guidance
- **Web App**: `backend/app/main.py` is the FastAPI entry point.
- **Frontend**: `frontend/src/` directory contains the React app with TanStack file-based routing.
- **Domain Services**: `backend/app/services/` contains business logic:
  - `PlanService` -- CRUD for plans, weeks, workouts; validation; progression recalculation.
  - `PlanBuilderService` -- wizard-to-plan generation, template resolution, zone calculation, clone.
  - `ActivityService` -- save/retrieve actual activities with zone JSON handling.
  - `ContextService` -- get user context (project, runner profile, training zones).
  - `GarminService` -- OAuth token-based Garmin Connect integration, activity fetching, telemetry enrichment.
- **Template Engine**: `backend/app/core/templates/` contains plan templates:
  - `base.py` -- shared periodisation logic, volume curves, plan generation from templates.
  - `running.py` -- 15 running plan templates (5K/10K/half/marathon/ultra x 3 levels).
  - `swimming.py` -- 24 swimming plan templates (pool 400/800/1500 + OW 1K/2.5K/5K/10K x 3 levels).
- **Zone Calculator**: `backend/app/core/zones.py` -- HR zones (Tanaka), pace zones, swim CSS zones.
- **Scripts**: Automation scripts reside in `backend/scripts/`. Always run them via `cd backend && uv run scripts/<script_name>.py`.
- **Models**:
    - `backend/app/core/database.py`: SQLModel database tables (`User`, `RunnerPlan`, `PlanWeek`, `PlanWorkout`, `RunnerProject`, `RunnerProfile`, `ActualActivity`, `PlanTemplate`, `FeatureFlag`).
    - `backend/app/models/domain.py`: Domain dataclasses and enums (`PlanType`, `ActivityType`, `WorkoutFormat`, `EventType`, `ExperienceLevel`, `PrimaryGoal`, `PainPoint`, `SwimmingEventType`).
    - `backend/app/schemas.py`: Pydantic DTOs for API requests/responses (`WizardInput`, `PlanPreview`, `ClonePlanRequest`, `WorkoutCreate/Update/Schema`, `WeekSchema`, `ContextSchema`, etc.).

### Guidelines:
- **Node Environment**: Always run `nvml` before executing any node/npm commands on the host machine.
- **Docker Environment**: The application runs natively in Docker.
  - **Environment**: This project is fully containerized. Use `docker-compose` for orchestration.
  - **Execution**: Run scripts/migrations inside the container: `docker exec running_app uv run ...`
  - **Changes**: Restart container (`docker restart running_app`) to apply backend code changes if hot-reload isn't active/working.
- **Timezone**: All automated logic and date-logging MUST use AWST (Perth, UTC+8).
- **Database**: Data structure changes require both a SQL migration script and a SQLModel model update. Do not edit legacy JSON files.
- **API Documentation**: Maintain `backend/tests/api_requests.http` as a live reference for all available API endpoints. Update it whenever routes change.
- **Testing**: Maintain the `backend/tests/` suite. Run with `cd backend && uv run pytest`. Currently 219 tests passing.
- **Style Rule**: Strictly no emojis in any responses, code, or documentation.

### Standard Operations:
- **Environment**: Run `nvml` before any node/npm command on the host to ensure correct Node version (LTS).
- **Start Backend**: `cd backend && uv run uvicorn app.main:app --reload`
- **Start Frontend**: `cd frontend && nvml && npm run dev`
- **Garmin Sync**: Via UI (Sync Button) or `POST /api/integrations/garmin/sync` with `X-Garmin-Token` header.
- **Run Tests**: `cd backend && uv run pytest`
- **Docker Stack**: `docker compose up --build` (dev) or `docker compose -f docker-compose.prod.yml up -d` (prod).

### Lessons Learned & Best Practices:
- **Git History First**: Before recreating "missing" files/configs, check `git log` or `git show` for prior existence in other branches.
- **Infrastructure Awareness**: When refactoring one layer (e.g., Frontend), explicitly verify integration points with Deployment/Infrastructure (Docker) to ensure no regressions.
- **Environment Parity**: Always check for environment variable usages (e.g., `DATABASE_URL`) that indicate alternative configurations (like Postgres) versus default local paths.

### Architectural Guidelines (Clean Architecture)
- **Thin Controllers**: API routers (`backend/app/routers/`) must be thin. They:
  - Strictly convert HTTP requests to Service calls.
  - Must use **Dependency Injection** (`Depends`) to access services.
  - Must NOT contain business logic or direct DB queries.
- **Domain Services (`backend/app/services/`)**:
  - Encapsulate all business rules and database interactions.
  - **Scoped**: Initialized with a `Session` (Dependency Injection style).
  - **Mapping Owner**: Responsible for converting SQLModel Entities to Pydantic DTOs (`schemas.py`).
- **Data Transfer Objects (DTOs)**: Use Pydantic models (Schemas) for all data moving in/out of the API.

### Validation Engine (Guardrails)
- **Location**: `backend/app/core/validation.py`
- **Rules**:
  - **Volume Progression**: Weekly volume increase capped at 15%.
  - **Long Run Ratio**: Single long run should not exceed 40% of weekly volume.
  - **Intensity Ratio**: High intensity work should not exceed 25% of weekly volume.
- **Enforcement**:
  - Validation runs on **Save/Update**.
  - Returns `ValidationWarningError` (used by UI to show warnings) or blocks saving if configured strictly.
  - Tests simulate these rules (and must mock them if testing simple CRUD).

### Migration System

- **Runner**: `backend/db/migrate.py` — forward-only, inspired by DbUp
- **Scripts**: `backend/db/migrations/NNN_description.sql` (3-digit zero-padded prefix)
- **Tracking**: `__schema_versions` table in Postgres (auto-created)
- **Run**: `docker exec running_app uv run python -m db.migrate` (or `uv run python -m db.migrate` locally from `backend/`)
- **Status**: append `--status` flag
- **Adding a migration**: create the next numbered `.sql` file; use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` for safety
- **Current migrations**:
  - `001_initial_schema.sql` — full schema as of 2026-02-10
  - `002_add_project_context_to_plan.sql` — `event`, `goal`, `event_date` on `runnerplan`
  - `003_add_wizard_input_to_plan.sql` — `wizard_input_json` on `runnerplan`
  - `004_add_feature_flags.sql` — `user_types_json` on `user`; `featureflag` table
- **Runtime startup** (`migrations_logic.py`): idempotent Python helpers that also run at app startup as a safety net for dev environments; they become no-ops once the SQL migration has been applied.

### Feature Flag System

- `FeatureFlag` table: `name` (unique), `enabled_for_json` (JSON array), `description`
- `User.user_types_json`: JSON array of type strings, default `["standard"]`
- Valid user types: `standard`, `alpha`, `beta`, `premium`
- `enabled_for_json` semantics: `[]` = off for all, `["*"]` = on for all, `["alpha","beta"]` = specific types only
- Service: `backend/app/services/feature_flags.py` (`FeatureFlagService`)
- API endpoints: `GET /api/flags` (resolved bool map for current user), `GET /api/admin/flags`, `PUT /api/admin/flags/{name}`
- Admin endpoints protected by `require_role("app_admin")` (`backend/app/core/auth.py`); dev bypass via `DEFAULT_USERNAME` + `ENVIRONMENT=development`
- `isSwimmingEnabled` seeded on startup (off by default); guards `POST /api/plans/generate-preview`, `POST /api/plans/from-wizard`, `PUT /api/plans/{id}/from-wizard`


- **Design Document**: `.ai/plan-builder-wizard.md` (Status: Implemented -- Phase 1 complete).
- **Backend**: `PlanBuilderService` orchestrates wizard inputs -> template selection -> zone calculation -> plan generation -> DB persistence.
- **Frontend**: 6-step wizard at `/plans/build` route with `useWizard` hook for step navigation and form state.
- **Templates**: Periodised plans with 5 phases (base, build, peak, taper, race). Volume curves use peak volume with step-back ratios. Each template defines session types per day, volume percentages, and workout prescriptions.
- **Zones**: Auto-calculated for beginners; optional custom override for intermediate/advanced. Stored on `RunnerProfile` as `training_zones_json` / `swim_zones_json`.
