# Training Assistant Instructions

When working in this workspace, always refer to the following files to maintain context of the marathon training plan:

1.  **Architecture**: This is a **FastAPI** application using **SQLModel** (SQLite) and **Jinja2/HTMX** for the frontend.
2.  **Source of Truth**:
    *   **Logic**: `app/` contains the web application, `scripts/` contains automation logic.
    *   **Data**: `database.db` is the primary persistence. `plan.json` and `context.json` are currently being transitioned into the DB but remain valid references.

### Project Structure Guidance
- **Web App**: `app/main.py` is the entry point. Routes are in `app/routers/`.
- **Domain Services**: `app/services/` contains business logic (`PlanService`, `ContextService`).
- **Scripts**: Automation scripts (Garmin sync, etc.) reside in `scripts/`. Always run them via `uv run scripts/dataset_name.py`.
- **Models**:
    - `app/core/database.py`: SQLModel database tables (`User`, `RunnerPlan`).
    - `app/schemas.py`: Pydantic DTOs for API requests/responses.

### Guidelines:
- **Timezone**: All automated logic and date-logging MUST use AWST (Perth, UTC+8).
- **Database**: When modifying data structure, prefer updating `app/core/database.py` over legacy JSON files if possible.
- **Testing**: Maintain the `tests/` suite. Run with `uv run pytest`.
- **Style Rule**: Strictly no emojis in any responses, code, or documentation.

### Standard Operations:
- **Start Server**: `uv run uvicorn app.main:app --reload`
- **Garmin Sync**: `uv run scripts/fetch_actuals.py` (Hourly via CI/CD)

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
