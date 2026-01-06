# Project Roadmap: 3h2Os

## Current Version: v0.0.6 (Training Block Kickoff)

## Phase 1: Foundation (Complete)
- [x] Structured 14-week training plan in Markdown.
- [x] Automated sync to Garmin Connect calendar.
- [x] Local HTML dashboard for plan visualization.
- [x] Migration to `uv` for modern dependency management.
- [x] **JSON-First Architecture:** `plan.json` and `context.json` as the single sources of truth.
- [x] **Automated Documentation:** `generate_plan_md.py` to keep `marathon_plan.md` and `context.md` in sync.

## Phase 2: Data Integration (Weeks 1-4)
- [x] **Planned vs. Actual:** Fetch Garmin activity data to show completion status on the dashboard.
- [x] **Weight Integration:** Mechanism to update current weight and track history via `update_weight.py`.
- [x] **GitHub Actions Automation:** Automated `fetch_actuals.py` to run nightly at 00:00 AWST.
- [x] **Fridge Mode:** Print-friendly weekly sheets available via dashboard and CLI.
- [ ] **Fueling Audit:** Log actual carb/sodium intake for Sunday PLRs to ensure 90/900 compliance.

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

## Phase 6: SaaS Transformation (Future)
- [ ] **Multi-User Architecture:** Decouple from personal repo to a scalable multi-tenant SaaS.
- [ ] **Database Layer:** Migrate from JSON flat-files to a NoSQL/Relational DB (e.g., Azure Cosmos DB for low-latency global distribution).
- [ ] **API Service:** Develop a REST/GraphQL API to handle Garmin webhooks and frontend requests.
- [ ] **Modern Frontend:** Transition to a React/Next.js dashboard with authenticated user profiles.
- [ ] **Cloud-Native Auth:** Implement secure login via GitHub OAuth or Clerk.
