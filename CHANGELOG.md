# Release Notes

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
