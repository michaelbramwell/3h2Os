# Project Roadmap: 3h2Os

## Current Version: v0.0.6 (Training Block Kickoff)

## Phase 1: Foundation (Complete)
- [x] Structured 14-week training plan in Markdown.
- [x] Automated sync to Garmin Connect calendar.
- [x] Local HTML dashboard for plan visualization.
- [x] Migration to `uv` for modern dependency management.
- [x] **JSON-First Architecture:** `plan.json` and `context.json` as the single sources of truth.
- [x] **Automated Documentation:** `generate_plan_md.py` to keep `marathon_plan.md` and `context.md` in sync.

## Phase 2: Data Integration & Intelligence (Weeks 1-4)
- [x] **Planned vs. Actual:** Fetch Garmin activity data to show completion status on the dashboard.
- [x] **Weight Integration:** Mechanism to update current weight and track history via `update_weight.py`.
- [x] **GitHub Actions Automation:** Automated `fetch_actuals.py` to run hourly.
- [x] **Fridge Mode:** Print-friendly weekly sheets available via dashboard and CLI.
- [x] **Zone Alignment:** Aligned pace zones with Strava ranges (Z1-Z6) and enriched documentation.
- [x] **Dynamic Validation:** Guardrails logic (`reflect_and_validate.py`) to manage baselines, volume caps, and intelligent baseline detection (ignoring Rest/Race weeks).
- [x] **Plan Recalculation:** "The Architect" tool (`update_plan.py`) to bulk-update future training load based on configurable growth factors.
- [x] **Dashboard 2.0:** Enhanced visual indicators for week statuses (Rest, Race, Taper, Marathon) and improved badges.
- [ ] **Fueling Audit:** Log actual carb/sodium intake for Sunday PLRs to ensure 90/900 compliance.

## Phase 2.5: Architecture Migration (Active)
- [x] **FastAPI Foundation:** Setup `app/` folder with `uvicorn`, routing, and testing support.
- [x] **Database Layer (SQLite):** Implemented SQLModel with `RunnerPlan`, `User`, and `PlanWeek` tables.
- [x] **Domain Services:** Created `PlanService` and `ContextService` to encapsulate business logic using dependency injection.
- [x] **Thin Controllers:** Refactored API routers to delegate logic strictly to services via DTOs.
- [ ] **Full Data Migration:** Completely retire `plan.json` and `context.json` in favor of the SQLite database.
- [ ] **Frontend Update:** Wire the dashboard to consume the new `/api/plans` and `/api/context` endpoints instead of static JSON.

## Phase 3: Performance Analytics (Weeks 5-10)
- [ ] **Efficiency Tracking:** Monitor Pace/HR decoupling for Wednesday Steady runs.
- [ ] **Cramp Correlation:** Log muscle fatigue levels and correlate with hydration/fueling data.
- [ ] **Shoe Tracker:** Monitor mileage on race-day shoes to ensure they are "broken in but not broken".

## Phase 4: Race Readiness (Weeks 11-14)
- [ ] **Taper Fatigue Monitor:** Track recovery metrics (RHR/Sleep) during the volume drop.
- [ ] **Bunbury Pacing Strategy:** Generate a 5km split-chart for a 3:45 - 3:55 finish.
- [ ] **Final Gear Checklist:** Digital verification for the Salomon vest and race-day kit.

## Phase 5: Post-Race Analysis
- [ ] **Race Report:** Automated summary of splits and fueling effectiveness.
- [ ] **Recovery Plan:** 4-week reverse-taper for injury prevention.

## Phase 6: SaaS Transformation (In Progress)
- [ ] **Multi-User Architecture:** Decouple from personal repo to a scalable multi-tenant SaaS.
- [x] **Database Layer:** Migrated to SQLModel (SQLite).
- [x] **API Service:** Developed FastAPI service.
- [ ] **Modern Frontend:** Refactoring to React (Vite + TanStack).
  - [x] Project Setup (Vite, Tailwind, TanStack Router/Query).
  - [ ] Feature Implementation.
- [ ] **Cloud-Native Auth:** Implement secure login via GitHub OAuth or Clerk.
- [ ] **AI Weekly Retrospective:** Implement a "Sunday Night Review" that analyzes actuals, weight, and fueling to suggest plan adjustments for the following week, with a simple "Accept/Decline" UX for the user.
