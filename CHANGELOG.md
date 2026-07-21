# Release Notes

## [Unreleased] - Remove Swimming

Swimming has been removed as a supported sport. The platform is now running-only.
Historical entries below (including the prior `[Unreleased] - Platform Hardening`,
Garmin, AWST, and AI-plan entries) are preserved as-is; this entry does not rewrite
history. Migration `016_remove_swimming.sql` encodes the schema portion of this work.

### Migration
- **`016_remove_swimming.sql`** (destructive): deletes existing `RunnerPlan` rows where `type='swimming'` (cascading weeks/workouts); deletes existing `ActualActivity` rows where `type` in `('swimming', 'swim', 'pool', 'lap_swimming', 'open_water_swimming')`; drops `runnerprofile.swim_zones_json`; deletes the `isSwimmingEnabled` feature flag row. Back up the production database before applying.

### Removed
- **Swimming as a supported sport**: no new swim plans can be created. The wizard is running-only and no longer renders a sport selector. The 24 swimming plan templates and `backend/app/core/templates/swimming.py` were deleted. `PlanType.SWIMMING`, `SwimmingVenue`, `SWIMMING_POOL_EVENTS`, `SWIMMING_OW_EVENTS`, `SWIMMING_EVENTS`, `SWIM_ACTIVITY_TYPES`, swim entries in `EVENT_DISTANCES_M` and `EventType`, and the swim-specific `PainPoint` values (`BREATHING`, `OPEN_WATER_ANXIETY`, `STROKE_EFFICIENCY`) were removed. Swim branches were removed from `zones.calculate_zones`, `plans._get_last_actual_volume`, `plans.get_active_plan_activity_types`, `plan_builder._resolve_template`, `context.get_context` (swim zones merge), `mappers._normalize_activity_type`, and `schemas._SPORT_TYPE_MAP`. Frontend `Sport.SWIMMING`, swim event types, `SwimmingPoolEvents`/`SwimmingOWEvents`/`SwimmingEvents` arrays, swim `EventLabels`, `swimPace` from `ContextSchema`, `isSwimmingEnabled` from `FeatureFlags`, and the `swimmingEnabled` prop chain through the wizard components were removed.
- **`isSwimmingEnabled` feature flag**: deleted. The `FeatureFlag` table, `FeatureFlagService`, `/api/flags` endpoints, and the `useFeatureFlags` hook remain in place for future flags; only the `isSwimmingEnabled` row is deleted.
- **`runnerprofile.swim_zones_json` column**: dropped.
- **Swimming guard in wizard router**: the 3 duplicated `isSwimmingEnabled` checks in `routers/wizard.py` were deleted entirely (no refactor needed).

### Retained (Historical Display)
- **Strava swim activity import**: `_SPORT_TYPE_MAP["Swim"] = "swimming"` is retained in `strava.py` so future Strava swim activities continue to import as historical actuals with `type='swimming'`. They appear in the activities list with a generic "Imported" badge and are excluded from volume calculations. They cannot be matched to a plan because no swim plans exist.
- **`ActivityType.SWIMMING = "Swimming"` enum member**: retained in `backend/app/models/domain.py` and the frontend `ActivityType` enum for display comparisons in `ActivityModal`, `ActualCard`, `WorkoutCard`, and `share.$token.tsx`. Historical Strava swim activities use this enum value for icon and pace formatting.
- **`formatSwimPace` formatter**: retained in `frontend/src/lib/formatters.ts` for historical display of swim activity paces (sec/100m).
- **Historical Garmin, AWST, and AI-plan CHANGELOG entries**: preserved unchanged. This entry supersedes the prior swimming-related entries without rewriting them.

## [Unreleased] - Platform Hardening

This entry supersedes prior Garmin, AWST, and AI-plan entries without rewriting history.
Historical entries below are retained as-is. Migration `015_platform_hardening.sql`
encodes the schema portion of this work.

### Migration
- **`015_platform_hardening.sql`**: adds `user.oidc_issuer` + `user.oidc_subject` (unique identity pair); `runnerprofile.timezone_name` (IANA); `actualactivity.started_at` (`TIMESTAMPTZ` UTC instant for Strava activity start, distinct from the provider-local `DATE`); new `strava_oauth_state` table (single-use, user-bound OAuth state); new `strava_webhook_job` table (durable, idempotent webhook jobs); converts all instant columns from `TIMESTAMP` to `TIMESTAMPTZ` (interpreting existing naive values as UTC); partial unique index ensuring at most one active plan per user; unique constraints on `runnerprofile.user_id`, `runnerproject.user_id`, `activityshare.activity_id`; deletes `isGarminEnabled` and `isAiEnabled` flag rows; strips the `garmin` key from existing `profile_sync_prefs_json`; drops `runnerprofile.garmin_running_zones_json`; changes the default `actualactivity.source` from `'garmin'` to `'manual'`; preserves historical Garmin rows and legacy Garmin columns as read-only.

### Removed
- **Garmin integration**: removed entirely from backend, frontend, dependencies, and tests. Historical Garmin activity rows (`source='garmin'`) are preserved as read-only records. No Garmin write paths exist. The `isGarminEnabled` feature flag and `garmin_running_zones_json` column were dropped.
- **AI plan option**: removed from the frontend. New requests with `generation_method='ai'` are rejected with 422 by Pydantic. Legacy plans with `generation_method='ai'` can still be opened and edited (normalized to `template` on edit). The `isAiEnabled` feature flag was dropped.

### Security
- **Host header bypass fix**: malformed `Host` authentication bypass closed. `TrustedHostMiddleware` added; allowed hosts are derived from `CORS_ORIGINS` / `DOMAIN`.
- **Tenant ownership enforcement**: all plan/week/workout mutations now enforce tenant ownership. Cross-tenant access returns 404.
- **JWT validation strengthened**: issuer, audience, and authorized party (`azp`) claims are now enforced in production. Users are resolved by `(oidc_issuer, oidc_subject)` on the `User` model; `username` and `email` are mutable profile attributes, not identity keys.

### Strava Webhook Integrity
- **Single-use OAuth state**: Strava OAuth state is now persisted, user-bound, and single-use. The nonce is hashed before storage; reuse or replay is rejected.
- **Durable webhook jobs**: webhook events are persisted as `strava_webhook_job` rows and processed idempotently by a background worker (`_strava_webhook_worker_loop` in `main.py`). The POST endpoint returns 200 immediately to meet Strava's ~2s acknowledgement requirement.
- **Share revocation**: delete events remove the activity row and revoke its public shares transactionally. Privacy update events refetch the activity; if inaccessible, the row and its shares are deleted. Deauthorization events delete the Strava token, revoke shares for all the user's Strava activities, and delete Strava-sourced activity rows. Historical Garmin/manual rows are preserved.
- **Exact-activity refetch**: ordinary update/create events refetch the exact activity by ID instead of scanning a 2-day window.
- **SSE fan-out**: events are pushed to browsers only after the worker successfully commits.

### Time Architecture
- **UTC TIMESTAMPTZ**: all instant columns converted from `TIMESTAMP` to `TIMESTAMPTZ` (existing naive values interpreted as UTC). APIs serialize instants as RFC 3339 with `Z` or `+00:00`.
- **Timezone-neutral DATE**: calendar dates remain `DATE` (`YYYY-MM-DD`). Examples: workout date, week start date, event date, birthday, provider-local activity date.
- **Per-user IANA timezone**: `RunnerProfile.timezone_name` stores an IANA timezone. Backend calendar business rules (current workout/week, past restrictions, next-Monday scheduling, race-day placement) use the user's timezone, not the container's. Falls back to UTC when absent or invalid.
- **Strava `started_at` vs `date`**: Strava activity `started_at` (UTC instant from `start_date`) is stored separately from `date` (provider-local calendar date from `start_date_local`). Plan completion is matched by `date`.
- **Browser display**: `frontend/src/lib/dateTime.ts` centralizes formatting. `formatInstant()` renders in the browser's timezone and locale; `formatCalendarDate()` is timezone-invariant. Hardcoded `en-AU` removed. Browser IANA timezone is synced to `RunnerProfile.timezone_name`. AWST (Perth, UTC+8) is no longer a project mandate.

### Plans
- **Atomic writes**: plan create/replace/activate/progression each run in a single transaction.
- **Sport-specific progression**: progression recalculation is sport-specific; the 62km fallback has been removed.
- **Race-day scheduling**: race workouts are scheduled on the exact event date for all 7 weekdays.
- **Safe frontend editing**: no destructive replace on plan-load failure; no auto-rebase.
- **Active-plan uniqueness**: a partial unique index ensures at most one active plan per user.

### Repository Hygiene
- **Tracked SQLite database removed from Git**. Per-context `.dockerignore` files added.

### Deployment Hardening
- **Test-gated**: deploy workflow runs backend and frontend test suites before building images. Failing tests block deploy.
- **Immutable images**: production images are tagged with the commit SHA; `:latest` is never used in prod.
- **Health-checked**: deploy waits for `GET /healthz` to return 200 on the new container before switching traffic.
- **Rollback on smoke-test failure**: post-deploy smoke test failure triggers automatic rollback to the previous image.
- **`/healthz` endpoint**: unauthenticated `{"status":"ok"}` probe added for container healthchecks and external smoke tests.

## [v1.2.0] - 2026-04-07

### Features & Enhancements
- **User Profile & Settings Page**: New `/settings` route showing all runner profile fields (weight, height, resting HR, VO2max, lactate threshold, FTP) with source-ownership badges (Garmin/Strava), inline editing for unowned fields, and a "Sync Now" action.
- **Per-Source Sync Preferences**: Fine-grained control over which source (Garmin or Strava) may write each profile field. Mutual exclusion enforced for shared fields (weight defaults to Strava).
- **Fitness Metrics Sync**: Garmin sync now pulls lactate threshold (HR + pace), VO2max, resting HR, and running pace zones from Garmin Connect, respecting user sync-pref toggles.
- **Activity Custom Names**: Users can rename any synced activity inline; stored in new `custom_name` column on `actualactivity`.
- **Race-Pace–Anchored Pace Zones**: `calculate_pace_zones()` now derives zones directly from race pace using Jack Daniels / Pfitzinger fractions (Recovery 70%, Easy 75%, Tempo 96%, Threshold 105%, VO2 Max 114%) when a target time is provided.
- **Garmin Feature Flag**: `isGarminEnabled` flag (disabled by default) gates all Garmin UI due to IP rate-limiting issues with the unofficial Garmin API.

### Backend & Architecture
- **`/api/profile` Router**: `GET`, `PATCH`, `PATCH /sync-prefs`, and `POST /sync-now` endpoints for profile management.
- **`profile_sync.py`**: Isolated helper module with `load_prefs`, `dump_prefs`, `can_write`, and `apply_toggle` — source-priority logic decoupled from routers and services.
- **Migrations 010–013**: Custom activity name, fitness metrics + sync prefs columns, Garmin running zones, Garmin feature flag seed.

### Testing
- **`test_profile.py`**: Coverage for all profile endpoints and `profile_sync` unit helpers.

## [v1.1.0] - 2026-03-08

### Features & Enhancements
- **Strava OAuth Integration**: Added Strava OAuth integration with activity sync capabilities.
- **Garmin Integration Update**: Updated Garmin integration for improved activity synchronization.
- **Feature Flags System**: Implemented feature flags system for A/B testing functionality.
- **Plan Wizard Enhancement**: Enhanced plan wizard with athlete profile and integration banner.
- **Test Coverage**: Added significant test coverage for calculations, formatters, and components.

### Backend & Architecture
- **API Router Refactoring**: Refactored monolithic API router into separate domain routers (plans, activities, flags, wizard, strava, garmin).
- **Database Migrations**: New database migrations for feature flags and profile fields.

## [v1.0.0] - 2026-02-22

### Features & Enhancements
- **Plan Edits**: Enabled the ability to modify future workouts within existing plans.
- **Week-by-Week Plans**: Added a "No Event (Build Weekly)" option to Step 1 of the wizard. This bypasses automated plan generation and routes users directly to the manual builder.
- **UI Improvements**: Resolved CSS grid layout issues in the manual workout builder and fixed a bug preventing decimal inputs in the distance fields.

### Backend & Architecture
- **Controller Cleanup**: Simplified backend title generation to strictly use the user-provided plan name. Updated corresponding endpoints, validation schemas (made `plan_name` compulsory in Step 1), and fixed broken test suites.
- **Migration System**: Replaced Alembic with a custom forward-only SQL migration runner using numbered `.sql` scripts (`db/migrations/`) tracked in a `__schema_versions` table.

## [v0.9.0] - 2026-02-12

### Features & Enhancements
- **Plan Builder Wizard**: Full multi-step wizard interface for creating periodised training plans. Guides users through sport/event selection, athlete profile, goals, plan configuration, and review before generating a complete plan.
- **Template Engine**: 39 plan templates (15 running + 24 swimming) covering beginner/intermediate/advanced levels across all supported event types. Templates encode periodisation phases (base, build, peak, taper, race), session patterns, and volume curves.
- **Advanced Swimming Templates**: Distinct advanced-level templates for pool (1500m) and open water (5K) with 6 sessions/week featuring intervals, threshold, and tempo simultaneously. Separated from intermediate templates which previously shared the same definitions.
- **Zone Calculator**: Auto-calculated training zones from athlete profile data -- HR zones (Tanaka formula), running pace zones (with optional VDOT refinement from target time), and swim CSS zones. Intermediate/advanced users can override with custom values.
- **Plan Preview**: Wizard generates a non-destructive preview (phase breakdown, volume curve, zones) before committing to the database.
- **Clone Plan**: Duplicate any existing plan with optional date offset for reuse or experimentation.

### Backend & Architecture
- **PlanBuilderService**: New service orchestrating wizard-to-plan generation, template resolution with fallbacks, zone calculation, and profile/project persistence.
- **Template Module**: New `core/templates/` package with `base.py` (shared periodisation logic, volume curves), `running.py` (15 templates), and `swimming.py` (24 templates).
- **New API Endpoints**: `POST /api/plans/generate-preview`, `POST /api/plans/from-wizard`, `POST /api/plans/{id}/clone`.
- **Data Model**: Added `RunnerProfile` (experience, events completed, pain points, zones), `RunnerProject` (event type, target time, goals), and `PlanTemplate` tables. Alembic migration for new columns and tables.
- **Domain Enums**: Added `EventType`, `ExperienceLevel`, `PrimaryGoal`, `PainPoint`, `SwimmingEventType` enums to `models/domain.py`.
- **Schemas**: Added `WizardInput` (with sub-schemas for each wizard step), `PlanPreview`, `ClonePlanRequest`, `HrZone` DTOs.

### Frontend
- **Wizard Components**: 6-step wizard UI (`StepSportEvent`, `StepAthleteProfile`, `StepGoalsFocus`, `StepPlanConfig`, `StepReview`, `WizardProgress`) with step navigation and form state accumulation.
- **Wizard Route**: New `/plans/build` route for the plan builder wizard.
- **Clone Dialog**: `ClonePlanDialog` component for duplicating plans from the plan switcher.
- **Wizard Hook**: `useWizard` custom hook managing step state machine and form data aggregation.

### Testing
- **Plan Builder Tests**: 35 new tests covering advanced swimming template distinctness, session composition, and template selection across all event/level combinations. Total test count: 219, all passing.

## [v0.8.0] - 2026-02-03

### Features & Enhancements
- **Multi-Plan Support**: Backend and UI refactored to support multiple training plans (e.g., Run, Swim) concurrently.
- **Swim Plan Integration**: Added specific support for swimming activities, formats, and pace zones.
- **Plan Management**: Added UI capability to delete plans and improved the plan creation flow.
- **Responsive Dashboard**: Implemented a sticky header and collapsible sidebar to improve usability on long plans and smaller screens.

### Backend & Architecture
- **Weight Tracking Removal**: Removed weight tracking features (tables and columns) as they are no longer in scope for this project.
- **Migration Fixes**: Resolved circular dependencies in Alembic migrations and cleaned up redundant logic.
- **Mapping Consistency**: Updated activity type mapping to align legacy "threshold" activities with the new "Threshold" workout format.
- **Testing**: Expanded test coverage for plan editing, specifically for week status updates.

### Frontend
- **Safety**: Added null checks in `WeekCard` to prevent runtime errors during plan editing.
- **State Management**: Improved query invalidation in `PlanSwitcher` to ensure UI consistency after plan deletion.

## [v0.7.0] - 2026-01-27

### Authentication & Security
- **Dynamic JWKS**: Refactored backend to fetch keys dynamically from Keycloak's JWKS endpoint, removing the need for static `public_key.pem` and improving security.
- **JWKS Caching**: Implemented internal caching for JWKS keys to optimize performance.
- **Identity Provider**: Hardened Keycloak configuration by disabling user registration in production.

### Infrastructure & CI/CD
- **Managed Storage**: Migrated production volumes to Hetzner managed volumes and parameterized volume paths for better infrastructure portability.
- **Test Automation**: Integrated automated backend and frontend test suites into the CI/CD pipeline.
- **Deployment Optimization**: Standardized container image naming for GHCR and streamlined builds by targeting AMD64 to resolve QEMU stability issues.
- **Legacy Cleanup**: Removed obsolete GitHub Pages workflows as the project moved to a containerized deployment.

### Backend & API
- **Router Robustness**: Reordered API routers and implemented dual-mount logic (root and `/api`) to ensure consistent routing behind reverse proxies.
- **CORS Management**: Externalized CORS configurations to environment variables for environment-specific security policies.
- **Reverse Proxy Support**: Optimized Keycloak and API configurations for HTTPS proxying, including proper redirect URI handling and HTTP listener settings.

### UI & UX
- **Branding Refresh**: Updated application iconography with the new 3h2Os wave logo and enhanced sidebar branding for better visibility.
- **Stability**: Fixed various TypeScript compilation errors, import issues, and mock configurations to ensure a stable frontend build.

### Documentation & AI
- **Roadmap**: Updated project roadmap to reflect the completion of core Authentication, Branding, and Deployment milestones.
- **AI Context**: Centralized AI context rules and updated `.gitignore` to maintain a clean development environment.

## [v0.6.0] - 2026-01-25

### Infrastructure & Deployment
- **Production Stack**: Established full deployment architecture for Hetzner Cloud using Docker Compose, Caddy (Edge Router/SSL), and GitHub Container Registry (GHCR).
- **CI/CD Pipeline**: Implemented multi-arch (Arm64/AMD64) build and deploy workflows via GitHub Actions.
- **Security**: Added secrets management and deployment checklists for secure production provisioning.

### Authentication (Keycloak)
- **Identity Provider**: Integrated **Keycloak** for centralized user management and OIDC/JWT authentication.
- **User-Centricity**: Refactored core domain services (`PlanService`, `GarminService`) to support multi-user context, moving away from hardcoded single-user logic.
- **JWT Handling**: Implemented robust JWT validation with RS256 signature verification (configurable for dev/prod).

### Logic & Validation
- **Activity Classification**: Centralized "Is Running?" logic to fix bugs where cross-training (Cycling) incorrectly triggered "Volume Spike" alerts.
- **Refactoring**: Moved validation rules and volume calculations into pure functions for better testability and reuse.

## [v0.5.0] - 2026-01-20

### Features
- **Workout Management**: Implemented full CRUD (Create, Read, Update, Delete) capabilities for workouts in the UI.
- **Enhanced Validation**: Added strict schemas for Distance (0-1000km sanity check) and Time of Day. Integrated `ValidationWarningError` handling in the API to surface guardrail warnings to the user.
- **UI/UX Improvements**: Overhauled the `EditWorkoutDialog` with better state management, "Delete" confirmation workflows, and smoother interactions.

### Security
- **Auth Awareness**: flagged lack of authentication on mutation endpoints and added architecture TODOs for future implementation.

### Refactor
- **Frontend Structure**: Consolidated component logic (moving state from `useState` to props in dialogs) and improved test coverage for UI components.
- **Code Quality**: Removed unused imports (`json`, `os`) and dead code across backend services based on automated review feedback.

## [v0.4.0] - 2026-01-18

### Architecture
- **Database First**: Completed the transition to a pure SQLModel database architecture. Removed all legacy JSON persistence logic.
- **Legacy Cleanup**: Deleted `backend/data/*.json` (plan, actuals, context) and static HTML dashboards (`dashboard.html`, `index.html`).
- **Date Agnostic**: Refactored automation scripts (`fetch_actuals.py`, `update_plan.py`) to remove hardcoded year dependencies, using dynamic current-date logic.

### Automation & Scripts
- **Unified Services**: All scripts (`fetch_actuals`, `reflect_and_validate`, `sync_to_garmin`) now inject `PlanService` and `ActivityService` to interact directly with the DB.
- **Garmin Sync Fix**: Resolved import path issues in `sync_to_garmin.py` to allow standalone execution.

### Testing
- **Validation Engine**: Added `tests/test_validation_engine.py` to test core "Guardrails" logic (Volume, 80/20 Rule) without file system dependencies.
- **Suite Cleanup**: Removed obsolete tests dependent on legacy JSON structures.

## [v0.3.0] - 2026-01-15

### Added
- **Architectural Overhaul (Phase 2.5)**:
    - **Domain Services**: Introduced `PlanService` and `ContextService` to encapsulate business logic and data mapping.
    - **Dependency Injection**: Implemented FastAPI's `Depends` system to inject scoped services into controllers.
    - **Thin Controllers**: API endpoints in `api.py` are now strictly responsible for HTTP handling.
    - **Centralized AI Context**: Created a dedicated `.ai/` directory for Agent Skills and Context to standardize tooling interactions.
- **Database Framework**:
    - **Relational Tables**: Implemented comprehensive SQLModel tables for `RunnerPlan`, `PlanWeek`, and `PlanWorkout`.
    - **Data Migration**: Logic to migrate legacy `context.json` and `plan.json` data into the SQLite database.
- **Infrastructure**:
    - **Docker Support**: Added `Dockerfile` and `docker-compose.yml` enabling full **PostgreSQL** support for containerized environments.
    - **Alembic Migrations**: Integrated Alembic for reliable database schema versioning across SQLite (Dev) and Postgres (Prod).
    - **OpenAPI 3.1**: Standardized API schemas and added `.http` files for VS Code REST Client testing.
- **Garmin Integration**: Added support for token authentication and validation scripts.

### Changed
- **Dashboard UX**: Added sticky headers to the main plan table for improved readability during vertical scrolling.
- **Testing**: Updated test suites to reflect the new dynamic scaling logic and domain service architecture.

## [v0.2.0] - 2026-01-13

### Added
- **Plan Intelligence**:
    - Introduced `scripts/update_plan.py` ("The Architect") to proactively recalculate future training blocks with configurable progression (defaults to 10% weekly build).
    - Enhanced `scripts/reflect_and_validate.py` ("The Guardrails") with smart baseline detection that looks back past "Rest", "Race", or "Taper" weeks to strictly enforce volume caps only against valid "Normal" weeks.
- **Dashboard 2.0**:
    - Visual overhaul for Week Statuses. Added distinct color coding and badges for **Recovery** (Slate), **Race** (Orange), **Taper** (Emerald), and **Marathon** (Yellow) weeks.
- **Pipelines**:
    - New `update-weight` GitHub Action for manual weight entry via GUI.
    - Integrated `pytest` test runners into all CI/CD pipelines to ensure data integrity before deployment.

### Changed
- **Training Plan**:
    - Recalculated weeks 4-14 to smooth out the progression curve following the Week 5 Rest/Race block.
    - Updated specific week statuses in `plan.json` to enable new visualization features.

### Fixed
- **Validation Logic**: Fixed a bug where coming off a Rest week would trigger false-positive "Volume Spike" warnings for the subsequent return to normal volume.

## [v0.1.1] - 2026-01-11

### Fixed
- **Static Build**: Updated `scripts/build_static.py` to correctly copy `data/` files (`actuals.json`, `plan.json`) to the output directory, ensuring the deployed dashboard has access to data.
- **Source Control**: Updated `.gitignore` to ensure data files are tracked for the build process while keeping the repository clean.

## [v0.1.0] - 2026-01-11

### Added
- **FastAPI Architecture**: Complete backend re-architecture using FastAPI and SQLModel, moving away from standalone scripts for the core application.
- **TypeScript Support**: Migrated inline JavaScript to a structured TypeScript codebase (`app/static/ts`) for better maintainability and type safety.
- **Static Site Builder**: Introduced `scripts/build_static.py` to compile the FastAPI assets back into a static `index.html` site for GitHub Pages compatibility.
- **Hybrid Deployment**: Updated CI/CD workflow to test the Python app and then build/deploy the static version automatically.
- **Test Suite**: Comprehensive test coverage (`test_app.py`, `test_generators.py`, etc.) for the new modular architecture.

### Changed
- **Project Structure**: Moved source code into `app/`, scripts to `scripts/`, and introduced `app/models/domain.py` as the shared data contract.
- **Dashboard Logic**: Extracted complex inline JS from `index.html` into `dashboard.ts`/`dashboard.js`.
- **UX Polish**: Improved "Training Effect" display with decimal formatting and visual color badges.

## [v0.0.7] - 2026-01-10

### Added
- **Trail Running**: Explicit support for trail running activities in the plan structure.
- **Dashboard Progress**: Added a "Progress" column to the dashboard table, displaying Target, Current, and Projected status.

### Changed
- **CI/CD Frequency**: Increased Garmin data fetching frequency from daily to **hourly** to provide near real-time updates.
- **Deployment Logic**: Configured the deployment pipeline to trigger automatically upon successful retrieval of "Actuals" from Garmin.

### Fixed
- **Data Accuracy**: Corrected the logic for calculating "Actual" distance totals to ensure better alignment with Garmin data.

## [v0.0.6] - 2026-01-06

### Added
- **Fridge Mode**: High-contrast, A4-optimized physical checklists available via the dashboard "Print Week" button and `generate_fridge_sheets.py`.

### Changed
- **Timezone Alignment**: Migrated all automated logic and Garmin data fetching from GMT/UTC to **AWST (Perth, UTC+8)** to ensure calendar synchronization.

## [Earlier Releases]

### Added
- **Weight Tracking**: Introduced `update_weight.py` and tracking history in `context.json` to monitor the 97kg -> 90kg target.
- **Nightly Sync**: Configured GitHub Actions to automatically fetch Garmin "Actuals" at 00:00 AWST daily.

### Changed
- **Dependency Management**: Fully migrated to `uv` for deterministic builds and faster environment setup.
- **API Modernization**: Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`.

### Fixed
- **Dashboard Layout**: Resolved layout squishing on mobile devices.
- **Sync Logic**: Improved Garmin API error handling and retry logic.
