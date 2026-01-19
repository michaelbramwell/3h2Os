# Training Assistant Instructions

When working in this workspace, always refer to the following files to maintain context of the marathon training plan:

1.  **Architecture**: This is a **FastAPI** application using **SQLModel** (SQLite/ostgreSQL) for the backend API, and a **React** (Vite) frontend using **TanStack Router/Query**.
2.  **Source of Truth**:
    *   **Logic**: `app/` contains the API, `frontend/` contains the UI, `scripts/` contains automation.
    *   **Data**: `database.db` (Local) or PostgreSQL (Docker) is the **single source of truth**. Legacy JSON files have been deprecated.

### Project Structure Guidance
- **Web App**: `backend/app/main.py` is the data API.
- **Frontend**: `frontend/` directory contains the React app.
- **Domain Services**: `backend/app/services/` contains business logic (`PlanService`, `ContextService`).
- **Scripts**: Automation scripts (Garmin sync, etc.) reside in `backend/scripts/`. Always run them via `cd backend && uv run scripts/dataset_name.py`.
- **Models**:
    - `backend/app/core/database.py`: SQLModel database tables (`User`, `RunnerPlan`).
    - `backend/app/schemas.py`: Pydantic DTOs for API requests/responses.

### Guidelines:
- **Timezone**: All automated logic and date-logging MUST use AWST (Perth, UTC+8).
- **Database**: Data structure changes must be done via SQLModel/Alembic. Do not edit legacy JSON files.
- **API Documentation**: Maintain `backend/tests/api_requests.http` as a live reference for all available API endpoints. Update it whenever routes change.
- **Testing**: Maintain the `backend/tests/` suite. Run with `cd backend && uv run pytest`.
- **Style Rule**: Strictly no emojis in any responses, code, or documentation.

### Standard Operations:
- **Start Backend**: `cd backend && uv run uvicorn app.main:app --reload`
- **Start Frontend**: `cd frontend && npm run dev`
- **Garmin Sync**: `cd backend && uv run scripts/fetch_actuals.py` (Hourly via CI/CD)

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
