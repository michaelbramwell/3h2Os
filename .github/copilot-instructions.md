# Training Assistant Instructions

When working in this workspace, always refer to the following files to maintain context of the marathon training plan:

1.  **Architecture**: This is a **FastAPI** application using **SQLModel** (SQLite) and **Jinja2/HTMX** for the frontend.
2.  **Source of Truth**:
    *   **Logic**: `app/` contains the web application, `scripts/` contains automation logic.
    *   **Data**: `database.db` is the primary persistence. `plan.json` and `context.json` are currently being transitioned into the DB but remain valid references.

### Project Structure Guidance
- **Web App**: `app/main.py` is the entry point. Routes are in `app/routers/`.
- **Scripts**: Automation scripts (Garmin sync, etc.) reside in `scripts/`. Always run them via `uv run scripts/dataset_name.py`.
- **Models**:
    - `app/core/database.py`: SQLModel database tables (`User`, `RunnerPlan`).
    - `app/models/domain.py`: Legacy data classes (`Week`, `Workout`).

### Guidelines:
- **Timezone**: All automated logic and date-logging MUST use AWST (Perth, UTC+8).
- **Database**: When modifying data structure, prefer updating `app/core/database.py` over legacy JSON files if possible.
- **Testing**: Maintain the `tests/` suite. Run with `uv run pytest`.
- **Style Rule**: Strictly no emojis in any responses, code, or documentation.

### Standard Operations:
- **Start Server**: `uv run uvicorn app.main:app --reload`
- **Garmin Sync**: `uv run scripts/fetch_actuals.py` (Hourly via CI/CD)

