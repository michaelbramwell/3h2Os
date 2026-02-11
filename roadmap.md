# Project Roadmap: 3h2Os

## Current Version: v0.9.0 (Plan Builder Wizard)

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
- [ ] **Data Persistence:** Migrate PostgreSQL data storage from VM local disk to attached Block Storage volume for durability across instance rebuilds.

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

## Phase 4: Performance Analytics (Planned)
- [ ] **Efficiency Tracking:** Monitor Pace/HR decoupling for Wednesday Steady runs.
- [ ] **Cramp Correlation:** Log muscle fatigue levels and correlate with hydration/fueling data.
- [ ] **Shoe Tracker:** Monitor mileage on race-day shoes to ensure they are "broken in but not broken".
- [ ] **AI Weekly Retrospective:** Implement a "Sunday Night Review" that analyzes actuals and fueling to suggest plan adjustments for the following week.

## Phase 5: AI-Assisted Plan Generation (Planned)
- [ ] **AI Plan Generator:** LLM-based plan generation as an alternative to templates, constrained by the validation engine guardrails.
- [ ] **Validation Loop:** Generate, validate, retry/flag workflow for AI-generated plans.
- [ ] **Premium Toggle:** Wizard step to select AI mode vs template mode.
- [ ] **Rate Limiting:** Usage tracking and billing integration for AI generations.

## Phase 6: Race Readiness (Planned)
- [ ] **Taper Fatigue Monitor:** Track recovery metrics (RHR/Sleep) during the volume drop.
- [ ] **Pacing Strategy:** Generate split charts for target finish times.
- [ ] **Final Gear Checklist:** Digital verification for race-day kit.

## Phase 7: Post-Race & Polish (Planned)
- [ ] **Race Report:** Automated summary of splits and fueling effectiveness.
- [ ] **Recovery Plan:** 4-week reverse-taper for injury prevention.
- [ ] **Plan Comparison:** Diff two plans side by side.
- [ ] **Plan Sharing:** Export as link or PDF.
- [ ] **Adaptive Re-planning:** Mid-plan adjustments based on actuals vs plan divergence.
