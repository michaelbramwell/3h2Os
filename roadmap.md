# Project Roadmap: 3h2Os

> **Platform hardening (post-v1.2.0):** the Garmin integration was removed entirely, the
> AI plan option was removed (new `generation_method='ai'` requests are rejected with
> 422), all instant columns were converted to `TIMESTAMPTZ`, the per-user IANA timezone
> model was introduced, Strava OAuth state became single-use/user-bound, webhook events
> are persisted as durable jobs processed by a background worker, and deployment was
> made test-gated, immutable (SHA-tagged), and health-checked (`/healthz`). Historical
> Garmin activity rows are preserved as read-only records. See migration
> `015_platform_hardening.sql` and `CHANGELOG.md`.

> **Swimming removal (post-v1.2.0):** swimming was removed as a supported sport. The
> 24 swimming plan templates and `swimming.py` were deleted, the wizard is running-only,
> `runnerprofile.swim_zones_json` was dropped, the `isSwimmingEnabled` feature flag row
> was deleted (the `FeatureFlag` table itself is retained for future use), and historical
> swim plans and swim-type actual activities were deleted (destructive). Future Strava
> swim activities continue to import as historical actuals with a generic "Imported"
> badge. See migration `016_remove_swimming.sql` and the `[Unreleased] - Remove Swimming`
> entry in `CHANGELOG.md`. Historical roadmap entries below are preserved with REMOVED
> annotations where they reference swimming.

## Current Version: v0.11.0 (Profile, Activity Editing & Zone Improvements)

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
  - [x] **Multi-Plan Support:** Implemented UI to switch between different training plans (e.g., 5K vs. Marathon) with filtering logic for plan-specific activities. ~~Running vs. Swimming~~ (swimming REMOVED by migration 016).
  - [x] **Plan Management:** Added ability to delete plans via the UI.
  - [x] **Responsive Dashboard:** Implemented sticky sidebar/header and collapsible sidebar logic for better UX on long training plans.
- [x] **Data Persistence:** Migrate PostgreSQL data storage from VM local disk to attached Block Storage volume for durability across instance rebuilds.

## Phase 3.5: Plan Builder Wizard (Complete)
- [x] **Plan Builder Wizard:** Multi-step guided flow (Sport/Event, Athlete Profile, Goals, Plan Config, Review) to generate complete periodised training plans.
- [x] **Template Engine:** 15 running plan templates across beginner/intermediate/advanced levels for all supported event types. ~~39 plan templates (15 running + 24 swimming)~~ (24 swimming templates REMOVED by migration 016).
  - [x] Running: 5K, 10K, Half Marathon, Marathon, Ultra (3 levels each).
  - ~~[x] Swimming Pool: 400m, 800m, 1500m (3 levels each).~~ REMOVED by migration 016.
  - ~~[x] Swimming Open Water: 1km, 2.5km, 5km, 10km (3 levels each, with advanced-specific templates).~~ REMOVED by migration 016.
- [x] **Zone Calculator:** Auto-calculated HR zones (Tanaka) and pace zones from athlete profile. Custom zone override for intermediate/advanced. ~~Swim CSS zones~~ REMOVED by migration 016.
- [x] **PlanBuilderService:** Orchestrates wizard inputs to template selection, zone calculation, plan generation, and DB persistence.
- [x] **Plan Preview:** Non-destructive preview endpoint showing phase breakdown and volume curve before committing.
- [x] **Clone Plan:** Duplicate existing plans with date offsets via `POST /api/plans/{id}/clone`.
- [x] **Data Model Expansion:** `RunnerProfile`, `RunnerProject`, and `PlanTemplate` tables with Alembic migration.
- [x] **Frontend Wizard:** Multi-step wizard components with `useWizard` hook for state management. Dedicated `/plans/build` route.
- [x] **Tests:** Plan builder template generation and validation compliance.

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
  - ~~[x] `isSwimmingEnabled` flag guards all three wizard mutation endpoints.~~ REMOVED by migration 016 (swimming is no longer a supported sport; the `FeatureFlag` table is retained for future use).
  - [x] Frontend `useFeatureFlags` hook with default merge and `staleTime` caching.
- [x] **API Restructuring:** Decomposed monolithic `api.py` router (597 lines removed) into domain-specific routers:
  - [x] `routers/plans.py` — plan CRUD, clone, activation, week/workout mutations.
  - [x] `routers/activities.py` — activity listing, context endpoints.
  - [x] `routers/wizard.py` — preview, create, update. ~~with swimming flag guard~~ REMOVED by migration 016.
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
  - [x] `008_seed_feature_flags.sql` — seed `isSwimmingEnabled` flag (deleted by 016).
- [x] **Cleanup:** Removed 10 legacy scripts (`fetch_actuals.py`, `sync_to_garmin.py`, `generate_garmin_tokens.py`, etc.) and static TypeScript build artifacts. Deleted obsolete test files (`test_sync_logic.py`, `test_zone_logic.py`, `test_timezone.py`).
- [x] **Tests:** New coverage for feature flag API, feature flag service, wizard defaults, Strava callback, formatters, and calculations.
- [x] **Data Persistence:** Migrate PostgreSQL data storage from VM local disk to attached Block Storage volume for durability across instance rebuilds.

## Phase 4.5: Profile, Activity Editing & Zone Improvements (Complete)

### User Profile & Sync Preferences
- [x] **`GET/PATCH /api/profile`:** Read and manually edit runner profile fields (weight, height, resting HR, VO2max, lactate threshold, FTP).
- [x] **`PATCH /api/profile/sync-prefs`:** Per-source, per-field toggle controlling whether Garmin or Strava may write each field. Mutual-exclusion enforced for shared fields (weight).
- [x] **`POST /api/profile/sync-now`:** On-demand profile re-sync from all connected sources.
- [x] **`profile_sync.py`:** Shared helper module with `load_prefs`, `dump_prefs`, `can_write`, and `apply_toggle` — source-priority logic isolated from routers and services.
- [x] **Settings page (`/settings`):** Full React UI displaying all profile fields with source-ownership badges (Garmin/Strava), inline edit for unowned fields, sync-pref toggles, and "Sync Now" action.

### Fitness Metrics & Migrations
- [x] **Migration 011:** `resting_hr`, `vo2max`, `lactate_threshold_hr`, `lactate_threshold_pace`, `profile_sync_prefs_json`, `profile_last_synced_at` columns on `runnerprofile`.
- [x] **Migration 012:** `garmin_running_zones_json` on `runnerprofile` — stores user's custom Garmin pace zones for highest-priority zone anchoring.
- [x] **Garmin fitness pull:** `GarminService` fetches lactate threshold (HR + pace), VO2max, resting HR, and running pace zones from Garmin Connect on sync; respects `can_write` prefs.

### Activity Custom Names
- [x] **Migration 010:** `custom_name TEXT` column on `actualactivity`.
- [x] **`ActivityModal`:** Inline rename UI — editable name field written back via `PATCH /api/activities/{id}`.
- [x] **`ActualCard`:** Displays `custom_name` when set, falling back to source name.

### Zone Calculation Improvements
- [x] **Race-pace–anchored zones:** `calculate_pace_zones()` now derives zones directly from race pace using Jack Daniels / Pfitzinger fractions (Recovery 70%, Easy 75%, Tempo 96%, Threshold 105%, VO2 Max 114%) when a target time is provided, replacing the cruder experience-level multiplier approach.

### Garmin Feature Flag
- [x] **Migration 013:** Seeds `isGarminEnabled` feature flag defaulting to `[]` (disabled), gating Garmin UI due to IP rate-limiting issues with the unofficial API.
- [x] **`useFeatureFlags`:** `isGarminEnabled` wired into `IntegrationsMenu` to hide/show Garmin connect and sync controls.

### Tests
- [x] **`test_profile.py`:** Coverage for `GET /profile`, `PATCH /profile`, `PATCH /profile/sync-prefs`, `POST /profile/sync-now`, and `profile_sync` unit helpers.

---

## Phase 4.6: Code Cleanup (In Progress)
- [x] **Implementation Plan:** `.ai/code-cleanup.md` — prioritised list of security fixes, type safety improvements, duplication removal, and test gaps identified during PR #45 review.

## Phase 4.7: Data-Driven Zone & Progression Improvements (Planned)
- [ ] **Lactate Threshold Zone Anchoring:** Use athlete lactate threshold HR as the primary anchor for HR zone calculation, replacing the Tanaka estimated max HR formula. All 5 HR zones derive from LT HR when available.
- [ ] **Karvonen HR Zones:** When resting HR is available, apply the Karvonen formula (heart rate reserve) for more physiologically accurate HR zone boundaries.
- [ ] **Lactate Threshold Pace Zones:** Use athlete lactate threshold pace as the direct pace zone anchor when no target time is provided, replacing the coarse experience-level fallback paces.
- [ ] **Strava HR Zone Passthrough:** Feed Strava-imported HR zone boundaries into zone calculation as an override path when no manual LT HR is present.
- [ ] **Load-Aware Plan Progression:** Replace pure-distance recalculation (`plans.py`) with stress-based progression using training load and training effect, so plan adaptation reflects training intensity not just volume. (Historical Garmin `aerobic_te`/`anaerobic_te` rows may inform this; no new Garmin data is fetched.)
- [ ] **VO2max Volume Ceiling:** Use athlete VO2max to inform per-athlete peak volume ceilings in template selection, rather than relying solely on `experience_level`.

## Phase 4.7: Comprehensive Test Suite (Planned)
- [ ] **Parameterised zone tests:** `calculate_zones()` across ages 18–70, both sexes, all experience levels (beginner/intermediate/advanced), all event types (5k/10k/half/marathon), with and without `target_time`. ~~with swim event types~~ REMOVED by migration 016.
- [ ] **HR zone correctness:** Tanaka formula verified at age boundaries; zone boundaries sequential and non-overlapping for every combination.
- [ ] **Pace zone anchoring:** Target-time-anchored zones verified against expected m/s values; ordering invariant (Recovery < Easy < Tempo < Threshold < Interval) holds across all inputs.
- [ ] **`_pace_zones_from_lt_pace()`:** Zone boundary correctness across a representative range of LT pace values (3:30–6:30/km).
- [ ] **`refresh_training_zones()` — all 2 priority paths:** Strava HR zones path and default `calculate_zones()` path; edge cases: no sources connected, `lactate_threshold_pace = null`, missing `RunnerProject`.
- [ ] **`ContextService` zones path:** `trainingZones` populated correctly from `training_zones_json`; malformed JSON handled gracefully without raising. ~~swim zones merged from `swim_zones_json`~~ REMOVED by migration 016.
- [ ] **`SyncService`:** `sync_strava` triggers zone refresh; zone not overwritten if sync pref disabled.
- [ ] **Shared fixtures:** Rebuild `conftest.py` with reusable `make_user`, `make_profile`, `make_project`, and `app_client` factories to eliminate per-file duplication.
- [ ] **Mock user matrix:** Extensive parameterised tests covering users of varying sex, age, ability, weight, and experience level across all plan types.

## Phase 5: Performance Analytics (Planned)
- [ ] **AI Weekly Retrospective:** Implement a "Sunday Night Review" that analyzes actuals and fueling to suggest plan adjustments for the following week.

## Phase 6: AI-Assisted Plan Generation (REMOVED)

The AI-assisted plan generation phase has been removed from the roadmap. The
`isAiEnabled` feature flag was deleted by migration `015_platform_hardening.sql`,
and the `generation_method='ai'` literal is rejected by Pydantic with 422 on new
requests. Legacy plans with `generation_method='ai'` can still be opened and
edited (normalized to `template` on edit). The platform supports only
template-based, manual, and manual-weekly plan generation.


