# Project Roadmap: 3h2Os

## Current Version: v0.0.8 (SaaS Deployment)

## Phase 1: Foundation (Complete)
- [x] Structured 14-week training plan in Markdown.
- [x] Automated sync to Garmin Connect calendar.
- [x] Local HTML dashboard for plan visualization.
- [x] Migration to `uv` for modern dependency management.
- [x] **JSON-First Architecture:** `plan.json` and `context.json` as the single sources of truth.
- [x] **Automated Documentation:** `generate_plan_md.py` to keep `marathon_plan.md` and `context.md` in sync.

## Phase 2: Data Integration & Intelligence (Weeks 1-4)
- [x] **Planned vs. Actual:** Fetch Garmin activity data to show completion status on the dashboard (UI Driven).
- [x] **GitHub Actions Automation:** Automated `fetch_actuals.py` (Deprecated in favor of UI sync).
- [x] **Fridge Mode:** Print-friendly weekly sheets available via dashboard and CLI.
- [x] **Zone Alignment:** Aligned pace zones with Strava ranges (Z1-Z6) and enriched documentation.
- [x] **Dynamic Validation:** Guardrails logic (`reflect_and_validate.py`) to manage baselines, volume caps, and intelligent baseline detection (ignoring Rest/Race weeks).
- [x] **Plan Recalculation:** "The Architect" tool (`update_plan.py`) to bulk-update future training load based on configurable growth factors.
- [x] **Dashboard 2.0:** Enhanced visual indicators for week statuses (Rest, Race, Taper, Marathon) and improved badges.
- [ ] **Fueling Audit:** Log actual carb/sodium intake for Sunday PLRs to ensure 90/900 compliance.

## Phase 2.5: Architecture Migration (Complete)
- [x] **FastAPI Foundation:** Setup `backend/app/` folder with `uvicorn`, routing, and testing support.
- [x] **Monorepo Structure:** Separated backend (`backend/`) and frontend (`frontend/`) codebases.
- [x] **Database Layer (SQLite):** Implemented SQLModel with `RunnerPlan`, `User`, and `PlanWeek` tables.
- [x] **Domain Services:** Created `PlanService` and `ContextService` to encapsulate business logic using dependency injection.
- [x] **Thin Controllers:** Refactored API routers to delegate logic strictly to services via DTOs.
- [x] **Full Data Migration:** Completely retire `plan.json` and `context.json` in favor of the SQLite database.
- [x] **Frontend Update:** Wire the dashboard to consume the new `/api/plans` and `/api/context` endpoints instead of static JSON.

## Phase 3: SaaS Transformation (Currently Active)
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

## Phase 4: Performance Analytics (Weeks 5-10)
- [ ] **Efficiency Tracking:** Monitor Pace/HR decoupling for Wednesday Steady runs.
- [ ] **Cramp Correlation:** Log muscle fatigue levels and correlate with hydration/fueling data.
- [ ] **Shoe Tracker:** Monitor mileage on race-day shoes to ensure they are "broken in but not broken".
- [ ] **AI Weekly Retrospective:** Implement a "Sunday Night Review" that analyzes actuals and fueling to suggest plan adjustments for the following week.

## Phase 5: Race Readiness (Weeks 11-14)
- [ ] **Taper Fatigue Monitor:** Track recovery metrics (RHR/Sleep) during the volume drop.
- [ ] **Bunbury Pacing Strategy:** Generate a 5km split-chart for a 3:45 - 3:55 finish.
- [ ] **Final Gear Checklist:** Digital verification for the Salomon vest and race-day kit.

## Phase 6: Post-Race Analysis
- [ ] **Race Report:** Automated summary of splits and fueling effectiveness.
- [ ] **Recovery Plan:** 4-week reverse-taper for injury prevention.
