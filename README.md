# 3h2Os: Sub-4 Marathon Training Plan

A data-driven marathon training project designed to solve the 30km cramp and achieve a sub-4 hour finish at the Bunbury Marathon (April 12, 2026).

## Project Overview

This repository contains a 14-week "smoothed" training plan, a local visualization dashboard, and a sync tool to push workouts directly to Garmin Connect.

- **Goal:** Sub-4:00 Marathon (5:41 min/km pace).
- **Secondary Goal:** Sub-22:00 Parkrun.
- **Strategy:** Progressive Long Runs (PLR), 90/900 Fueling Rule, and Mechanical Resilience (Strength).
- **Status:** 14-week plan synced to Garmin Connect.

## Structure

- `plan.json`: The source of truth for training data (used by sync tool and dashboard).
- `context.json`: The source of truth for runner profile and goals.
- `generate_plan_md.py`: Script to generate Markdown files from JSON.
- `marathon_plan.md`: Human-readable reference (auto-generated).
- `context.md`: Runner profile and strategy (auto-generated).
- `index.html`: The dashboard (hosted on GitHub Pages).
- `sync_to_garmin.py`: Python script to sync the plan to your Garmin Calendar.
- `fetch_actuals.py`: Python script to fetch completed activities from Garmin.
- `roadmap.md`: Future features and development phases.
- `pyproject.toml`: Project configuration and dependencies (managed by `uv`).

## Getting Started

### 1. Setup Environment
This project uses a hybrid Python/Node.js stack.
- **Python**: Managed by `uv`.
- **Frontend**: Managed by `npm` (TypeScript).

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Sync Python dependencies
uv sync

# 3. Install Frontend dependencies
cd app/static
npm install
npm run build  # Compiles TypeScript to JS
cd ../..
```

### 2. Run Local Application
The project runs as a FastAPI application for local development.

```bash
# Start the server (runs on localhost:8000)
uv run uvicorn app.main:app --reload
```
Visit `http://localhost:8000` to view the dashboard.

### 3. Training Logic & Tools

#### Validation Engine (The Guardrails)
To analyze your actual running data against the plan and safety-check the future weeks:
```bash
uv run scripts/reflect_and_validate.py
```
This script will:
- Compare Actuals vs Plan.
- Enforce 15% Volume Cap & 80/20 Intensity Rule.
- Automatically adjust future weeks in `data/plan.json`.
- **Save a new plan version** to the local SQLite database (`data/database.db`).

#### Sync to Garmin
To push the current `plan.json` to your Garmin Calendar:
```bash
uv run scripts/sync_to_garmin.py
```

### 4. Deployment (Static Site)
GitHub Pages hosts a static version of the site. The `scripts/build_static.py` script "freezes" the dynamic FastAPI app into static HTML/JSON files.

- **Automated**: Runs via GitHub Actions on every push.
- **Manual**: `uv run scripts/build_static.py`

## Architecture & Data Flow

1.  **Input**: `data/actuals.json` (Synced from Garmin) & `data/plan.json` (The Master Plan).
2.  **Processing**: `reflect_and_validate.py` reads inputs -> applies logic -> updates Plan -> saves to Database.
3.  **Visualization**: FastAPI (`app/`) serves the Plan from Database to the Browser.
4.  **Deployment**: Build script copies JSON & HTML to root for GitHub Pages.

### 4. Sync to Garmin
1. Copy `.env.example` to `.env`.
2. Add your Garmin Connect credentials.
3. Run the sync script:
```bash
uv run sync_to_garmin.py
```

### 5. Updating the Plan
If you need to modify the training schedule:
1. Edit `plan.json`.
2. Update the Markdown reference:
   ```bash
   uv run generate_plan_md.py
   ```
3. Sync to Garmin:
   ```bash
   uv run sync_to_garmin.py
   ```

### 5. Tracking Progress
You can manually pull your actual running data from Garmin:
```bash
uv run fetch_actuals.py
```
This updates `actuals.json` and the dashboard.

**Automation:** This project includes a GitHub Action that runs nightly to fetch your latest Garmin activities and update the dashboard automatically. To enable this, add `GARMIN_EMAIL` and `GARMIN_PASSWORD` to your repository secrets.

### 6. Weight Management
To update your current weight and track progress:
```bash
uv run python update_weight.py 96.5
```

### 7. Running Tests
To ensure the system is working correctly:
```bash
uv run pytest
```

## Training Philosophy
- **Monday:** Rest & Recovery.
- **Wednesday:** Double sessions (Steady AM / Intervals PM).
- **Thursday:** Trail runs for mechanical load.
- **Sunday:** Progressive Long Runs (PLR) with full fueling practice.

## Running the Application

The project uses a standard FastAPI + HTMX architecture.

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Run the Server** (Development Mode):
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   Open [http://localhost:8000](http://localhost:8000).

3. **Run Automation Scripts**:
   Scripts have been moved to the `scripts/` directory:
   ```bash
   uv run scripts/fetch_actuals.py
   uv run scripts/sync_to_garmin.py
   ```

## Project Structure

- `app/`: The web application (FastAPI).
  - `core/`: Database configuration (`database.db` via SQLModel).
  - `routers/`: API endpoints and page rendering.
  - `templates/`: HTML/Jinja2 templates.
- `scripts/`: Standalone automation tools (Garmin sync, MD generation).
- `data/`: JSON source files (legacy) and SQLite DB.

## Database

The app uses **SQLite** locally.
- **Connection**: `sqlite:///database.db`
- **Tools**: Use DBeaver or standard generic SQL clients to inspect.
- **Models**: Defined in `app/core/database.py`.

## Legacy Files (Transitioning)
