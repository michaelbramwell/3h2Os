# 3h2Os: Sub-4 Marathon Training Plan

A data-driven marathon training project designed to solve the 30km cramp and achieve a sub-4 hour finish at the Target Marathon.

## Project Overview

This repository contains a 14-week "smoothed" training plan, a local visualization dashboard, and a sync tool to push workouts directly to Garmin Connect.

- **Goal:** Sub-4:00 Marathon (5:41 min/km pace).
- **Secondary Goal:** Sub-22:00 Parkrun.
- **Strategy:** Progressive Long Runs (PLR), 90/900 Fueling Rule, and Mechanical Resilience (Strength).
- **Status:** 14-week plan synced to Garmin Connect.

## Project Structure

- **`frontend/`**: The React-based user interface (Vite, TanStack). See [`frontend/README.md`](frontend/README.md).
- **`backend/`**: The FastAPI backend API, database models, and scripts. See [`backend/app/README.md`](backend/app/README.md).
  - **`app/`**: API Source code.
  - **`scripts/`**: Automation scripts for Garmin sync and data processing.
  - **`data/`**: Database files (`database.db`). Legacy JSON files are in `.bak` state.
- `marathon_plan.md`: Human-readable reference (auto-generated).

## Getting Started

This is a hybrid Python/Node.js project.

### 1. Backend Setup
See [`backend/app/README.md`](backend/app/README.md) for instructions on setting up the FastAPI server, database, and running scripts.
All backend commands (like `uv run`) must be executed from the `backend/` directory.

### 2. Frontend Setup
See [`frontend/README.md`](frontend/README.md) for instructions on running the React dashboard.
- **Python**: Managed by `uv`.
- **Frontend**: Managed by `npm` (TypeScript).

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Setup Backend
cd backend
uv sync
cd ..

# 3. Setup Frontend
cd frontend
npm install
npm run build
```

## Running with Docker (Optional)

You can run the entire stack (Frontend, Backend, Database) using Docker.

```bash
docker compose up --build
```

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Auth**: Keycloak (Port 8080 or 8443)
- **Database**: PostgreSQL (Internal)

### 3. Run Local Application
The project runs as a FastAPI application for local development.

```bash
# Start the server (runs on localhost:8000)
cd backend
uv run uvicorn app.main:app --reload
```
Visit `http://localhost:8000` to view the dashboard (if you are serving the built frontend via static files).
For React development, run `npm run dev` in `frontend/` and visit `http://localhost:5173`.

### 4. Training Logic & Tools

#### Validation Engine ("The Guardrails")
To analyze your actual running data against the plan and safety-check the future weeks:
```bash
cd backend
uv run scripts/reflect_and_validate.py
```
This script acts as the "Guardrails" for your training:
- **Reactive**: Compares Actuals vs Plan.
- **Safety**: Enforces volume caps based on your *current* baseline (looking back past rest/race weeks).
- **Compliance**: Enforces 80/20 Intensity Rules.
- **Output**: Automatically adjusts specific future weeks if safety rules are violated and saves to DB.

#### Plan Updates ("The Architect")
To aggressively recalculate the entire future plan based on a new strategy:
```bash
cd backend
uv run scripts/update_plan.py
```
This script is the "Architect":
- **Proactive**: Rewrites future targets from the current week onwards.
- **Strategy**: Applies a configurable growth factor (e.g., 7% weekly build) to "Normal" weeks.
- **Intelligence**: Respects structure (Rest drops to 65% baseline, Taper drops to 60%, Race/Marathon weeks preserved).

#### Sync to Garmin
To push the current `plan.json` to your Garmin Calendar:
```bash
cd backend
uv run scripts/sync_to_garmin.py
```

### 5. Deployment (Static Site)
GitHub Pages hosts a static version of the site. The `scripts/build_static.py` script "freezes" the dynamic FastAPI app into static HTML/JSON files.

- **Automated**: Runs via GitHub Actions on every push.
- **Manual**: `cd backend && uv run scripts/build_static.py`

## Architecture & Data Flow

1.  **Input**: `backend/data/actuals.json` (Synced from Garmin) & `backend/data/plan.json` (The Master Plan).
2.  **Processing**: `reflect_and_validate.py` reads inputs -> applies logic -> updates Plan -> saves to Database.
3.  **Visualization**:
    - **FastAPI**: `app/` serves dynamic content locally.
    - **Frontend**: React-based dashboard consumes API.
4.  **Deployment**: Build script copies JSON & HTML to root for GitHub Pages.

### 4. Sync to Garmin
*Feature deprecated pending security updates/UI integration.*
Original command was:
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

### 6. Running Tests
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

4. **Run Static Version Locally**:
   To preview exactly what will be deployed to GitHub Pages:
   ```bash
   # Build the static site
   uv run scripts/build_static.py
   
   # Serve the current directory
   python3 -m http.server 8080
   ```
   Open [http://localhost:8080](http://localhost:8080).

## Project Structure

- `app/`: The web application (FastAPI).
  - `core/`: Database configuration (PostgreSQL via SQLModel).
  - `routers/`: API endpoints and page rendering.
  - `templates/`: HTML/Jinja2 templates.
- `scripts/`: Standalone automation tools (Garmin sync, MD generation).
- `data/`: JSON source files (legacy) and SQLite DB.

## Database

The app uses **PostgreSQL** in production/Docker and **SQLite** for local testing/dev if configured.
- **Production**: PostgreSQL via Docker.
- **ORM**: Defined in `app/core/database.py`.

## Legacy Files (Transitioning)
