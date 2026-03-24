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
  - `StravaService` -- OAuth + webhook-driven Strava integration, activity sync, athlete profile import.
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
- **Testing**: Maintain the `backend/tests/` suite. Run with `cd backend && uv run pytest`. Currently 336 tests passing.
- **Style Rule**: Strictly no emojis in any responses, code, or documentation.

### Standard Operations:
- **Environment**: Run `nvml` before any node/npm command on the host to ensure correct Node version (LTS).
- **Start Backend**: `cd backend && uv run uvicorn app.main:app --reload`
- **Start Frontend**: `cd frontend && nvml && npm run dev`
- **Garmin Sync**: Via UI (Sync Button) or `POST /api/integrations/garmin/sync` with `X-Garmin-Token` header.
- **Run Tests**: `cd backend && uv run pytest`
- **Docker Stack**: `docker compose up --build` (dev) or `docker compose -f docker-compose.prod.yml up -d` (prod).
- **Deploy to prod**: `act -j deploy` (`.actrc` configures `--secret-file .secrets` and `--var-file .vars` automatically)
- **Strava Sync**: Via UI integrations menu or `POST /api/integrations/strava/sync`
- **Garmin Sync**: Via UI (Sync Button) or `POST /api/integrations/garmin/sync` with `X-Garmin-Token` header.

### Lessons Learned & Best Practices:
- **Git History First**: Before recreating "missing" files/configs, check `git log` or `git show` for prior existence in other branches.
- **Infrastructure Awareness**: When refactoring one layer (e.g., Frontend), explicitly verify integration points with Deployment/Infrastructure (Docker) to ensure no regressions.
- **Environment Parity**: Always check for environment variable usages (e.g., `DATABASE_URL`) that indicate alternative configurations (like Postgres) versus default local paths.
- **Deployment env vars**: When adding new secrets/variables to `deploy.yml`, also update `.secrets` locally and the GitHub `prod` environment via `gh secret set` / `gh variable set`.
- **Caddy routing**: Always use `handle` blocks — never mix bare `reverse_proxy` with `handle` blocks in the same site; bare directives win and shadow all `handle` blocks.

### Environment Configuration

- **Single `.env` file** at repo root — used by both `docker compose` and `find_dotenv()` in the backend.
- **`.env.example`** at repo root is the canonical template covering all vars (infra, DB, Keycloak, Strava, app).
- **`backend/.env.example`** mirrors the backend-specific subset — kept for standalone backend use.
- **`.secrets`** at repo root supplies secrets to `act` for local prod deployment (mirrors GitHub Environment secrets). Never committed (gitignored).
- **`.secrets.example`** is the template for `.secrets`.
- **`.vars`** at repo root supplies non-secret variables to `act` (mirrors GitHub Environment variables). Never committed (gitignored).
- **`.vars.example`** is the template for `.vars`.
- **`.actrc`** configures `act` to use `--secret-file .secrets` and `--var-file .vars` automatically.
- **GitHub Environment (`prod`)** holds secrets and variables used by the GitHub Actions deploy workflow. Managed via `gh secret set` / `gh variable set`.

Key env var categories:
- Infra: `IMAGE_NAME`, `DOMAIN`, `ACME_EMAIL`, `VOLUME_PATH`
- Database: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`
- Keycloak: `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD`, `KC_HTTP_RELATIVE_PATH`
- Strava: `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_REDIRECT_URI`, `STRAVA_STATE_SECRET`, `STRAVA_WEBHOOK_SECRET`, `STRAVA_WEBHOOK_VERIFY_TOKEN`
- App: `FRONTEND_URL`, `CORS_ORIGINS`, `SECRET_KEY`

### Deployment

- Production is deployed via `act` (runs the GitHub Actions `deploy.yml` workflow locally):
  ```bash
  act -j deploy
  ```
- `.actrc` at repo root configures `act` with `--secret-file .secrets`, `--var-file .vars` automatically.
- `.secrets` = GitHub Environment secrets (gitignored). `.secrets.example` is the template.
- `.vars` = GitHub Environment variables (gitignored). `.vars.example` is the template.
- The `deploy` job assembles the prod `.env` from GitHub secrets/variables and SCPs it to the server along with `docker-compose.prod.yml`, `Caddyfile`, and Keycloak config.
- When adding new vars to the deploy workflow, update three places: `deploy.yml` (write step), `.secrets` (local act), and GitHub `prod` environment (remote).

### Strava Integration

- **OAuth flow**: frontend redirects to Strava → Strava redirects to `{STRAVA_REDIRECT_URI}` (frontend `/strava/callback` route) → frontend POSTs code+state to `POST /api/strava/exchange`.
- **Scopes**: `activity:read_all,profile:read_all`
- **Webhook**: `GET/POST /strava/webhook/{STRAVA_WEBHOOK_SECRET}` — secret path makes URL unguessable. Must register subscription with Strava once after first prod deploy.
- **Two Strava apps**: one for dev (`localhost` callback domain), one for prod (`3h2os.com`). Each has its own `client_id`/`client_secret`.
- **Auto-sync**: webhook events trigger a 2-day activity sync for the affected athlete automatically.
- **Webhook registration** (one-time after deploy):
  ```bash
  curl -X POST https://www.strava.com/api/v3/push_subscriptions \
    -F client_id=<STRAVA_CLIENT_ID> \
    -F client_secret=<STRAVA_CLIENT_SECRET> \
    -F callback_url=https://3h2os.com/strava/webhook/<STRAVA_WEBHOOK_SECRET> \
    -F verify_token=<STRAVA_WEBHOOK_VERIFY_TOKEN>
  ```

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
- **Runtime startup** (`db.migrate`): forward-only SQL migration runner that also runs at app startup via lifespan; migrations become no-ops once applied.

### Feature Flag System

- `FeatureFlag` table: `name` (unique), `enabled_for_json` (JSON array), `description`
- `User.user_types_json`: JSON array of type strings, default `["standard"]`
- Valid user types: `standard`, `alpha`, `beta`, `premium`
- `enabled_for_json` semantics: `[]` = off for all, `["*"]` = on for all, `["alpha","beta"]` = specific types only
- Service: `backend/app/services/feature_flags.py` (`FeatureFlagService`)
- API endpoints: `GET /api/flags` (resolved bool map for current user), `GET /api/admin/flags`, `PUT /api/admin/flags/{name}`
- Admin endpoints protected by `require_role("app_admin")` (`backend/app/core/auth.py`); dev bypass via `DEFAULT_USERNAME` + `ENVIRONMENT=development`
- `isSwimmingEnabled` seeded on startup (off by default); guards `POST /api/plans/generate-preview`, `POST /api/plans/from-wizard`, `PUT /api/plans/{id}/from-wizard`


### Real-Time Events (SSE)

- **Endpoint**: `GET /api/events` — Server-Sent Events stream; one persistent connection per browser tab per user.
- **Auth**: `EventSource` cannot send custom headers. The OIDC access token is passed via `?token=` query param. `verify_jwt_middleware` in `backend/app/core/auth.py` accepts token from query param as a fallback to the `Authorization` header.
- **Backend**: `backend/app/routers/events.py` — `_connections` dict maps `user_id → set[asyncio.Queue]`. `push_event(user_id, event, data)` is the helper called by other routers to fan-out to all open tabs for a user. 30-second keepalive comments prevent proxy timeouts.
- **Frontend hook**: `frontend/src/hooks/useSSE.ts` — retrieves the OIDC access token via `userManager.getUser()`, opens `EventSource`, listens for `activities_updated`, and calls `queryClient.invalidateQueries(['actuals'])` to refresh the UI.
- **Mounted in**: `frontend/src/routes/index.tsx` — `useSSE(auth.isAuthenticated)` so the connection is active whenever the user is logged in.
- **Strava webhook chain**: `POST /strava/webhook/{secret}` → `StravaService.handle_webhook_event()` returns `user_id` → router calls `push_event(user_id, "activities_updated", {...})` → all connected tabs for that user receive the event and invalidate their actuals cache.

### Plan Builder Wizard

- **Design Document**: `.ai/plan-builder-wizard.md` (Status: Implemented -- Phase 1 complete).
- **Backend**: `PlanBuilderService` orchestrates wizard inputs -> template selection -> zone calculation -> plan generation -> DB persistence.
- **Frontend**: 6-step wizard at `/plans/build` route with `useWizard` hook for step navigation and form state.
- **Templates**: Periodised plans with 5 phases (base, build, peak, taper, race). Volume curves use peak volume with step-back ratios. Each template defines session types per day, volume percentages, and workout prescriptions.
- **Zones**: Auto-calculated for beginners; optional custom override for intermediate/advanced. Stored on `RunnerProfile` as `training_zones_json` / `swim_zones_json`.
