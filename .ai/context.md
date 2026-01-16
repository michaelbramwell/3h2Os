# Training Assistant Instructions

When working in this workspace, always refer to the following files to maintain context of the marathon training plan:

1.  **Architecture**: This is a **FastAPI** application using **SQLModel** (SQLite/ostgreSQL) for the backend API, and a **React** (Vite) frontend using **TanStack Router/Query**.
2.  **Source of Truth**:
    *   **Logic**: `app/` contains the API, `frontend/` contains the UI, `scripts/` contains automation.
    *   **Data**: `database.db` (Local) or PostgreSQL (Docker) is the primary persistence. `plan.json` and `context.json` are currently being transitioned into the DB but remain valid references.

### Project Structure Guidance
- **Web App**: `app/main.py` is the data API.
- **Frontend**: `frontend/` directory contains the React app.
- **Domain Services**: `app/services/` contains business logic (`PlanService`, `ContextService`).
- **Scripts**: Automation scripts (Garmin sync, etc.) reside in `scripts/`. Always run them via `uv run scripts/dataset_name.py`.
- **Models**:
    - `app/core/database.py`: SQLModel database tables (`User`, `RunnerPlan`).
    - `app/schemas.py`: Pydantic DTOs for API requests/responses.

### Guidelines:
- **Timezone**: All automated logic and date-logging MUST use AWST (Perth, UTC+8).
- **Database**: When modifying data structure, prefer updating `app/core/database.py` over legacy JSON files if possible.
- **API Documentation**: Maintain `tests/api_requests.http` as a live reference for all available API endpoints. Update it whenever routes change.
- **Testing**: Maintain the `tests/` suite. Run with `uv run pytest`.
- **Style Rule**: Strictly no emojis in any responses, code, or documentation.

### Standard Operations:
- **Start Backend**: `uv run uvicorn app.main:app --reload`
- **Start Frontend**: `cd frontend && npm run dev`
- **Garmin Sync**: `uv run scripts/fetch_actuals.py` (Hourly via CI/CD)

### Lessons Learned & Best Practices:
- **Git History First**: Before recreating "missing" files/configs, check `git log` or `git show` for prior existence in other branches.
- **Infrastructure Awareness**: When refactoring one layer (e.g., Frontend), explicitly verify integration points with Deployment/Infrastructure (Docker) to ensure no regressions.
- **Environment Parity**: Always check for environment variable usages (e.g., `DATABASE_URL`) that indicate alternative configurations (like Postgres) versus default local paths.

### Architectural Guidelines (Clean Architecture)
- **Thin Controllers**: API routers (`app/routers/`) must be thin. They:
  - Strictly convert HTTP requests to Service calls.
  - Must use **Dependency Injection** (`Depends`) to access services.
  - Must NOT contain business logic or direct DB queries.
- **Domain Services (`app/services/`)**:
  - Encapsulate all business rules and database interactions.
  - **Scoped**: Initialized with a `Session` (Dependency Injection style).
  - **Mapping Owner**: Responsible for converting SQLModel Entities to Pydantic DTOs (`schemas.py`).
- **Data Transfer Objects (DTOs)**: Use Pydantic models (Schemas) for all data moving in/out of the API.
