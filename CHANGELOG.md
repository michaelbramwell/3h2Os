# Release Notes

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
