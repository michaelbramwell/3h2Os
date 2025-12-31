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
This project uses `uv` for fast, reliable dependency management.
```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies and create venv
uv sync
```

### 2. Local Dashboard
To view the plan in your browser:
```bash
# Start a local server
uv run python -m http.server 8000
# Open http://localhost:8000/index.html
```

### 3. GitHub Pages
The dashboard is automatically hosted at:
`https://michaelbramwell.github.io/3h2Os/`

### 3. Sync to Garmin
1. Copy `.env.example` to `.env`.
2. Add your Garmin Connect credentials.
3. Run the sync script:
```bash
uv run sync_to_garmin.py
```

### 4. Updating the Plan
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
To pull your actual running data from Garmin and update the dashboard:
```bash
uv run fetch_actuals.py
```
This will update `actuals.json` and the dashboard will display your completed runs (distance and pace) alongside the planned workouts.

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
