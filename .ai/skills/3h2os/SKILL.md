---
name: 3h2os-skills
description: Multi-sport training plan platform operational skills/tools.
---

This skill defines the operational capabilities for the 3h2Os training plan platform. It supports both running and swimming plan creation, management, and Garmin Connect integration.

## Training Operations

> **Infrastructure Note**: This project runs in Docker.
> - **Container**: Execute scripts inside the container: `docker exec running_app uv run [script_path]`.
> - **Orchestration**: Use `docker-compose` for managing services.
> - **Environment**: Ensure Docker Desktop is running before attempting operations.

### Plan Builder Wizard
Creates periodised training plans via a guided multi-step wizard.
- **Frontend Route**: `/plans/build`
- **Preview Endpoint**: `POST /api/plans/generate-preview` -- returns plan skeleton without saving.
- **Create Endpoint**: `POST /api/plans/from-wizard` -- generates and persists full plan.
- **Templates**: 39 templates (15 running + 24 swimming) across beginner/intermediate/advanced.
- **Zone Calculation**: Auto-calculated HR, pace, and swim CSS zones from athlete profile.

### Clone Plan
Duplicate an existing plan with optional date offset.
- **Endpoint**: `POST /api/plans/{id}/clone`
- **Inputs**: Plan ID, optional new title and date offset.

### Fetch Actuals (Garmin Sync)
Retrieves recent completed activities from Garmin Connect and persists them to the database.
- **Trigger**: Web UI (Sync Button) or API call with Token.
- **Endpoint**: `POST /api/integrations/garmin/sync`
- **Inputs**: Garmin Token (Header `X-Garmin-Token`), Database
- **Outputs**: Updates PostgreSQL. Includes detailed metric splits and zone distribution.

### Reflect & Validate
Compares executed workouts against the plan. Enforces safety guardrails (15% volume cap, 80/20 intensity distribution) and creates adaptations for future weeks if necessary.
- **Script**: `backend/scripts/reflect_and_validate.py`
- **Command**: `cd backend && uv run scripts/reflect_and_validate.py`
- **Inputs**: Database (Plan and Actuals)
- **Outputs**: Updates database, logs validation warnings.

### Sync to Garmin
Pushes structured workouts from the plan to the Garmin Connect Calendar.
- **Script**: `backend/scripts/sync_to_garmin.py`
- **Status**: Deprecated pending UI integration for Token Auth.

---

## Plan Management

### List Plans
- **Endpoint**: `GET /api/plans`
- **Returns**: All plans for the authenticated user.

### Create Empty Plan
- **Endpoint**: `POST /api/plans`
- **Inputs**: Title, plan type (run/swim).

### Delete Plan
- **Endpoint**: `DELETE /api/plans/{id}`

### Activate Plan
- **Endpoint**: `PUT /api/plans/{id}/activate`

### Workout CRUD
- **Create**: `POST /api/workouts`
- **Update**: `PUT /api/workouts/{id}`
- **Delete**: `DELETE /api/workouts/{id}`

### Week Update
- **Endpoint**: `PUT /api/weeks/{id}`

---

## Development

### Run Dev Server
Starts the FastAPI backend for local development.
- **Command**: `cd backend && uv run uvicorn app.main:app --reload`
- **Address**: `http://localhost:8000`

### Run Frontend Dev
Starts the React frontend for local development.
- **Command**: `cd frontend && nvml && npm run dev`
- **Address**: `http://localhost:5173`

### Run Tests
- **Backend**: `cd backend && uv run pytest` (219 tests)
- **Frontend**: `cd frontend && npm test`

### Docker Stack
- **Dev**: `docker compose up --build`
- **Prod**: `docker compose -f docker-compose.prod.yml up -d`
