---
name: 3h2os-skills
description: Automated marathon training coach skills/tools.
---

This skill defines the operational capabilities for the 3h2Os marathon training project. It is used to automate the feedback loop between the plan and actual execution.

## Training Operations

### Fetch Actuals
Retrieves recent completed activities from Garmin/Strava sources and persists them to the local dataset.
- **Script**: [`../../../backend/scripts/fetch_actuals.py`](../../../backend/scripts/fetch_actuals.py)
- **Command**: `cd backend && uv run scripts/fetch_actuals.py`
- **Inputs**: Garmin Credentials (Env Vars), `data/actuals.json` (for differential sync)
- **Outputs**: Updates `data/actuals.json`, `data/database.db`

### Reflect & Validate
The "Brain" of the operation. Compares executed runs against the plan. It enforces safety guardrails (15% volume cap, 80/20 intensity distribution) and creates adaptations for future weeks if necessary.
- **Script**: [`../../../backend/scripts/reflect_and_validate.py`](../../../backend/scripts/reflect_and_validate.py)
- **Command**: `cd backend && uv run scripts/reflect_and_validate.py`
- **Inputs**: `data/actuals.json`, `data/plan.json`
- **Outputs**: Updates `data/plan.json` (if adaptation needed), Logs validation warnings.

### Sync to Garmin
Pushes structured workouts from the JSON plan to the Garmin Connect Calendar for execution on the watch.
- **Script**: [`../../../backend/scripts/sync_to_garmin.py`](../../../backend/scripts/sync_to_garmin.py)
- **Command**: `cd backend && uv run scripts/sync_to_garmin.py`
- **Inputs**: `data/plan.json`
- **Outputs**: API calls to Garmin Connect.

### Update Weight
Updates the runner's current weight in the context profile, used for mechanics and fueling calculations.
- **Script**: [`../../../backend/scripts/update_weight.py`](../../../backend/scripts/update_weight.py)
- **Command**: `cd backend && uv run scripts/update_weight.py [KG]`
- **Inputs**: Weight in KG (float)
- **Outputs**: Updates `data/context.json`, `data/database.db`

---

## Documentation & Reporting

### Generate Plan Markdown
Converts the machine-readable JSON plan and context into human-readable Markdown files for GitHub viewing.
- **Script**: [`../../../backend/scripts/generate_plan_md.py`](../../../backend/scripts/generate_plan_md.py)
- **Command**: `cd backend && uv run scripts/generate_plan_md.py`
- **Outputs**: `marathon_plan.md`, `context.md`

### Generate Fridge Sheets
Generates printable A4 weekly summaries ("Fridge Sheets") for analog tracking.
- **Script**: [`../../../backend/scripts/generate_fridge_sheets.py`](../../../backend/scripts/generate_fridge_sheets.py)
- **Command**: `cd backend && uv run scripts/generate_fridge_sheets.py`
- **Outputs**: `fridge/*.md`

---

## Deployment

### Build Static Site
Freezes the dynamic FastAPI application into a static HTML/JS bundle for hosting on GitHub Pages.
- **Script**: [`../../../backend/scripts/build_static.py`](../../../backend/scripts/build_static.py)
- **Command**: `cd backend && uv run scripts/build_static.py`
- **Outputs**: `index.html`, `dashboard.html` (and static assets)

### Run Dev Server
Starts the FastAPI backend for local development and UI testing.
- **Command**: `cd backend && uv run uvicorn app.main:app --reload`
- **Address**: `http://localhost:8000`
