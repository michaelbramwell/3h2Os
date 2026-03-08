# Project Roadmap: 3h2Os

## Current Version: v0.10.0 (Strava & Garmin Integration)

## Phase 1: Foundation (Complete)
- [x] Structured 14-week training plan in Markdown.
- [x] Automated sync to Garmin Connect calendar.
- [x] Local HTML dashboard for plan visualization.
- [x] Migration to `uv` for modern dependency management.
- [x] **JSON-First Architecture:** `plan.json` and `context.json` as the single sources of truth.
- [x] **Automated Documentation:** `generate_plan_md.py` to keep `marathon_plan.md` and `context.md` in sync.

## Phase 2: Data Integration & Intelligence (Complete)
- [x] **Planned vs. Actual:** Fetch Garmin activity data to show completion status on the dashboard (UI Driven).
- [x] **GitHub Actions Automation:** Automated `fetch_actuals.py` (Deprecated in favor of UI sync).
- [x] **Fridge Mode:** Print-friendly weekly sheets available via dashboard and CLI.
- [x] **Zone Alignment:** Aligned pace zones with Strava ranges (Z1-Z6) and enriched documentation.
- [x] **Dynamic Validation:** Guardrails logic (`reflect_and_validate.py`) to manage baselines, volume caps, and intelligent baseline detection (ignoring Rest/Race weeks).
- [x] **Plan Recalculation:** "The Architect" tool (`update_plan.py`) to bulk-update future training load based on configurable growth factors.
- [x] **Dashboard 2.0:** Enhanced visual indicators for week statuses (Rest, Race, Taper, Marathon) and improved badges.

## Phase 2.5: Architecture Migration (Complete)
- [x] **FastAPI Foundation:** Setup `backend/app/` folder with `uvicorn`, routing, and testing support.
- [x] **Monorepo Structure:** Separated backend (`backend/`) and frontend (`frontend/`) codebases.
- [x] **Database Layer (SQLite):** Implemented SQLModel with `RunnerPlan`, `User`, and `PlanWeek` tables.
- [x] **Domain Services:** Created `PlanService` and `ContextService` to encapsulate business logic using dependency injection.
- [x] **Thin Controllers:** Refactored API routers to delegate logic strictly to services via DTOs.
- [x] **Full Data Migration:** Completely retire `plan.json` and `context.json` in favor of the SQLite database.
- [x] **Frontend Update:** Wire the dashboard to consume the new `/api/plans` and `/api/context` endpoints instead of static JSON.

## Phase 3: SaaS Transformation (Complete)
- [x] **Cloud Database:** Migrated from SQLite to PostgreSQL 15 via Alembic.
- [x] **Identity & Access Management (IAM):**
  - [x] Deployed **Keycloak** 26 (Quay.io) as the Identity Provider (IdP).
  - [x] Configured OIDC (OpenID Connect) flow for Frontend (React) via `react-oidc-context`.
  - [x] Secured Backend (FastAPI) with Bearer Token validation.
  - [x] **Dynamic JWKS:** Enabled zero-downtime key rotation by fetching signing keys directly from Keycloak.
  - [x] Disabled public registration for production security.
- [x] **Infrastructure & Deployment:**
  - [x] Containerized entire stack (Frontend, Backend, Postgres, Keycloak, Caddy).
  - [x] Configured **Caddy** as reverse proxy (Automatic HTTPS via Let's Encrypt).
  - [x] Setup **GitHub Actions** CI/CD pipeline for automated build and deploy to Hetzner VM.
  - [x] Implemented production-grade routing (`/api` vs `/`) to handle proxy path stripping.
- [x] **Branding & UI:**
  - [x] Created custom "3h2Os" Wave branding (SVG).
  - [x] Updated application title and favicon.
  - [x] Integrated branding into Sidebar UI.
  - [x] **Multi-Plan Support:** Implemented UI to switch between different training plans (e.g., Running vs. Swimming) with filtering logic for plan-specific activities.
  - [x] **Plan Management:** Added ability to delete plans via the UI.
  - [x] **Responsive Dashboard:** Implemented sticky sidebar/header and collapsible sidebar logic for better UX on long training plans.
- [x] **Data Persistence:** Migrate PostgreSQL data storage from VM local disk to attached Block Storage volume for durability across instance rebuilds.

## Phase 3.5: Plan Builder Wizard (Complete)
- [x] **Plan Builder Wizard:** Multi-step guided flow (Sport/Event, Athlete Profile, Goals, Plan Config, Review) to generate complete periodised training plans.
- [x] **Template Engine:** 39 plan templates (15 running + 24 swimming) across beginner/intermediate/advanced levels for all supported event types.
  - [x] Running: 5K, 10K, Half Marathon, Marathon, Ultra (3 levels each).
  - [x] Swimming Pool: 400m, 800m, 1500m (3 levels each).
  - [x] Swimming Open Water: 1km, 2.5km, 5km, 10km (3 levels each, with advanced-specific templates).
- [x] **Zone Calculator:** Auto-calculated HR zones (Tanaka), pace zones, and swim CSS zones from athlete profile. Custom zone override for intermediate/advanced.
- [x] **PlanBuilderService:** Orchestrates wizard inputs to template selection, zone calculation, plan generation, and DB persistence.
- [x] **Plan Preview:** Non-destructive preview endpoint showing phase breakdown and volume curve before committing.
- [x] **Clone Plan:** Duplicate existing plans with date offsets via `POST /api/plans/{id}/clone`.
- [x] **Data Model Expansion:** `RunnerProfile`, `RunnerProject`, and `PlanTemplate` tables with Alembic migration.
- [x] **Frontend Wizard:** 6 step components with `useWizard` hook for state management. Dedicated `/plans/build` route.
- [x] **Tests:** 219 passing tests including 35 for plan builder template validation.

## Phase 4: Strava & Garmin Integration (Complete)
- [x] **Strava OAuth2 Integration:** Full authorization code flow with HMAC-signed state tokens. Token auto-refresh (5-min expiry buffer). Disconnect/reconnect support.
  - [x] `StravaService` — token exchange, refresh, activity fetch, athlete profile import, zone import.
  - [x] `StravaToken` table with `005_add_strava.sql` migration.
  - [x] Frontend OAuth redirect via `/strava/callback` route with StrictMode-safe `useRef` guard.
- [x] **Activity Sync & Deduplication:** Strava-over-Garmin precedence when both sources provide the same activity (matched by date + 1% distance tolerance). Garmin `training_load`/`aerobic_te`/`anaerobic_te` preserved on merge.
- [x] **Zone Enrichment:** Progressive fallback — Strava Summit zones, then Streams API computation, then empty. HR, pace, and power zone distribution per activity.
  - [x] `compute_zones_from_streams` — second-by-second bucketing from Strava Streams API (`heartrate`, `velocity_smooth`, `watts`).
  - [x] Athlete zone boundary import from `GET /athlete/zones` (custom zones only).
- [x] **Athlete Profile Import:** Merge Strava athlete data (`weight`, `gender`, `ftp`) into `RunnerProfile` on connect and sync. Never overwrites manually-entered wizard data.
- [x] **Strava Webhooks:** `POST /strava/webhook/{secret}` with `STRAVA_WEBHOOK_SECRET` path-based authentication. Subscription verification via `hub.*` query param aliases.
- [x] **Sync Orchestration:** `SyncService` coordinates Garmin/Strava sync with plan progression recalculation. Non-fatal error handling for profile import and zone loading.
- [x] **Feature Flag System:**
  - [x] `FeatureFlag` table with user-type-based targeting (`standard`, `alpha`, `beta`, `premium`, `*` wildcard).
  - [x] `FeatureFlagService` with `is_enabled()` resolution, admin CRUD.
  - [x] `GET /api/flags` (resolved booleans), `GET/PUT /api/admin/flags` (role-protected).
  - [x] `isSwimmingEnabled` flag guards all three wizard mutation endpoints.
  - [x] Frontend `useFeatureFlags` hook with default merge and `staleTime` caching.
- [x] **API Restructuring:** Decomposed monolithic `api.py` router (597 lines removed) into domain-specific routers:
  - [x] `routers/plans.py` — plan CRUD, clone, activation, week/workout mutations.
  - [x] `routers/activities.py` — activity listing, context endpoints.
  - [x] `routers/wizard.py` — preview, create, update with swimming flag guard.
  - [x] `routers/strava.py` — OAuth flow, sync, webhooks.
  - [x] `routers/garmin.py` — Garmin sync endpoint.
  - [x] `routers/flags.py` — flag resolution and admin management.
  - [x] `routers/deps.py` — shared FastAPI dependencies (session, user resolution, service factories).
- [x] **Frontend Updates:**
  - [x] `IntegrationsMenu` — unified Strava/Garmin connection UI with connect, disconnect, and sync.
  - [x] `ActivityModal` — zone distribution display (HR, pace, power), split details, training effect.
  - [x] `RecentActivities` — source badges (Strava/Garmin), priority-based sync buttons.
  - [x] `WeekStats` — sticky header with sync controls.
  - [x] Wizard `IntegrationBanner` — prompts to connect Strava/Garmin for profile defaults.
  - [x] `useStravaStatus` hook — React Query backed status polling.
  - [x] Privacy policy page (`/privacy`).
  - [x] Strava brand assets and "Powered by Strava" attribution.
- [x] **Schema & Migrations:**
  - [x] `005_add_strava.sql` — `strava_token` table, `source`/`strava_activity_id` on `actualactivity`.
  - [x] `006_add_profile_strava_fields.sql` — `ftp`, `strava_athlete_id` on `runnerprofile`.
  - [x] `007_add_profile_birthday.sql` — `birthday` on `runnerprofile` for dynamic age calculation.
  - [x] `008_seed_feature_flags.sql` — seed `isSwimmingEnabled` flag.
- [x] **Cleanup:** Removed 10 legacy scripts (`fetch_actuals.py`, `sync_to_garmin.py`, `generate_garmin_tokens.py`, etc.) and static TypeScript build artifacts. Deleted obsolete test files (`test_sync_logic.py`, `test_zone_logic.py`, `test_timezone.py`).
- [x] **Tests:** 336 passing tests (up from 219). New coverage: feature flag API (547 lines), feature flag service (235 lines), wizard defaults (241 lines), Strava callback, formatters, calculations.
- [x] **Data Persistence:** Migrate PostgreSQL data storage from VM local disk to attached Block Storage volume for durability across instance rebuilds.

## Phase 4.5: Code Cleanup (Planned)
- [ ] **Implementation Plan:** `.ai/code-cleanup.md` — prioritised list of security fixes, type safety improvements, duplication removal, and test gaps identified during PR #45 review.

## Phase 5: Performance Analytics (Planned)
- [ ] **Efficiency Tracking:** Monitor Pace/HR decoupling for Wednesday Steady runs.
- [ ] **Cramp Correlation:** Log muscle fatigue levels and correlate with hydration/fueling data.
- [ ] **Shoe Tracker:** Monitor mileage on race-day shoes to ensure they are "broken in but not broken".
- [ ] **AI Weekly Retrospective:** Implement a "Sunday Night Review" that analyzes actuals and fueling to suggest plan adjustments for the following week.

## Phase 6: AI-Assisted Plan Generation (Planned)
- [ ] **AI Plan Generator:** LLM-based plan generation as an alternative to templates, constrained by the validation engine guardrails.
- [ ] **Validation Loop:** Generate, validate, retry/flag workflow for AI-generated plans.
- [ ] **Premium Toggle:** Wizard step to select AI mode vs template mode.
- [ ] **Rate Limiting:** Usage tracking and billing integration for AI generations.


