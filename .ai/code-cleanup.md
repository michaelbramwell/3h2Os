# Code Cleanup Implementation Plan

Status: Planned -- identified during PR #45 review (Strava & Garmin Integration).

This document catalogues all code quality, security, type safety, duplication, and test
coverage issues found during the comprehensive review of the Phase 4 feature branch.
Items are grouped by priority and ordered for incremental implementation.

---

## Priority 1: Security

These should be addressed before the next production deploy.

### 1.1 Missing authorization on plan mutation endpoints

`backend/app/routers/plans.py`

- `set_active_plan` (line ~84) has no `user: User = Depends(get_current_user)` dependency.
  Any authenticated user can activate any plan by ID.
- `update_week_endpoint` (line ~159) injects `user` but never passes it to `service.update_week`.
- `delete_workout_endpoint` (line ~235) injects `user` but never passes it to `service.delete_workout`.

**Fix:** Add user dependency to `set_active_plan`. Pass `user.id` to the service layer in
all three endpoints and scope the DB queries to `WHERE user_id = :user_id`.

### 1.2 DEFAULT_USERNAME environment guard

`backend/app/routers/deps.py:26-28`

The `DEFAULT_USERNAME` fallback in `get_current_user` lacks the `ENVIRONMENT == "development"`
guard that `auth.py`'s `verify_jwt_middleware` has. If `DEFAULT_USERNAME` is accidentally set
in production, all unauthenticated requests silently resolve to that user.

**Fix:** Add `and os.environ.get("ENVIRONMENT") == "development"` to the condition.

### 1.3 Error detail leaks internal state

Multiple routers return `detail=str(e)` in HTTP responses:

- `backend/app/routers/strava.py:124` -- `f"Strava API error: {str(e)}"`
- `backend/app/routers/flags.py:42,69,96` -- `detail=str(e)`
- `backend/app/routers/wizard.py` -- similar pattern in exception handlers

**Fix:** Return generic error messages to the client. Log `str(e)` server-side at WARNING
level. Example:

```python
except Exception as e:
    logger.warning("Strava sync failed: %s", e, exc_info=True)
    raise HTTPException(status_code=502, detail="External service error")
```

### 1.4 JWT token expiry verification

`backend/app/core/auth.py:199`

The options dict passes `"exp": True` but `python-jose` uses `"verify_exp"` as the option
key. If `exp` is silently ignored, expired tokens would be accepted.

**Fix:** Verify the correct option key for the JWT library in use. Test by presenting an
expired token and confirming a 401 response.

---

## Priority 2: Backend Code Quality

### 2.1 Replace deprecated `datetime.utcnow()`

Appears in: `strava.py:173,180,195,196,237`, `database.py:18,62,63,97`.

`datetime.utcnow()` is deprecated since Python 3.12 and returns naive datetimes. Will cause
issues on Postgres if timezone interpretation ever differs.

**Fix:** Replace all occurrences with `datetime.now(timezone.utc)`. Import `timezone` from
`datetime` module.

### 2.2 Webhook handler does sync inline

`backend/app/services/strava.py:668-692` (via `routers/strava.py`)

The `handle_webhook_event` method fetches activities, saves them, and recalculates plan
progression synchronously within the HTTP request. Strava requires webhook responses within
a few seconds. Slow sync or plan recalculation could cause Strava to disable the subscription.

**Fix:** Use FastAPI `BackgroundTasks` to defer the sync work. Return 200 immediately.

```python
@router.post("/strava/webhook/{secret}")
async def strava_webhook(
    ..., background_tasks: BackgroundTasks
):
    # Validate subscription / event
    background_tasks.add_task(handle_webhook_sync, event_data, ...)
    return {"status": "ok"}
```

### 2.3 Extract duplicated swimming guard

`backend/app/routers/wizard.py:45-51, 74-80, 138-144`

The identical 4-line swimming flag check is copy-pasted three times. The hardcoded string
`"isSwimmingEnabled"` also appears in 3 places.

**Fix:** Extract to a helper or FastAPI dependency:

```python
_SWIMMING_FLAG = "isSwimmingEnabled"

def _check_swimming_flag(wizard_input: WizardInput, user: User, flag_service: FeatureFlagService):
    if wizard_input.sport_event.sport == "swimming" and not flag_service.is_enabled(_SWIMMING_FLAG, user):
        raise HTTPException(status_code=403, detail="Swimming plans are not enabled for your account.")
```

### 2.4 Rename `HrZone` schema to `ZoneDistribution`

`backend/app/schemas.py:439-447`

`HrZone` is used for HR zones, pace zones, AND power zones. The name is misleading.
`activities.py` also uses `HrZone` to deserialize pace and power zone data.

**Fix:** Rename to `ZoneDistribution` (or `ZoneBucket`). Update all references in
`schemas.py`, `activities.py`, and `strava.py`.

### 2.5 Add pagination safety limit to Strava fetch

`backend/app/services/strava.py:410-429`

The `fetch_activities` while-loop has no upper bound on `page`. A pathological Strava
response (always returning a full page) would loop forever.

**Fix:** Add `max_pages = 50` guard (5000 activities is more than sufficient).

### 2.6 Clean up inline imports and dead code

- `strava.py:305-306` -- redundant `from datetime import date as date_type` (already
  imported at module level).
- `strava.py:305` -- inline `import json` (already used elsewhere in module).
- `flags.py:55,85` -- inline `import json` in function bodies.
- `strava.py:114` -- `STRAVA_STREAMS_MAX_AGE_DAYS` env var parsed without error handling;
  non-integer value raises unhandled `ValueError`.
- `activities.py:240-246` -- unreachable second `if not user` branch (dead code).
- `auth.py:219` -- unnecessary f-string prefix `f"Could not validate credentials"`.

### 2.7 Validate feature flag user types

`backend/app/services/feature_flags.py` `set_flag` method (line ~86)

No validation that `enabled_for` values are from the valid set (`standard`, `alpha`, `beta`,
`premium`, `*`). An admin could set `["typo"]` and it would never match.

**Fix:** Validate against `USER_TYPES` (from `database.py`) plus `"*"`.

### 2.8 Type hint accuracy in strava.py

`backend/app/services/strava.py:698-700`

```python
hr_thresholds: List[Dict] = None,
pace_thresholds: List[Dict] = None,
power_thresholds: List[Dict] = None,
```

Should be `Optional[List[Dict]] = None` for type safety.

### 2.9 Inconsistent error response shapes

Three different patterns exist across routers:
1. Typed Pydantic response models (Strava auth, flags).
2. Ad-hoc dicts (`{"status": "disconnected"}`, `{"synced": N, "days": 7}`).
3. FastAPI `HTTPException` detail strings.

**Fix:** Define response models for the ad-hoc endpoints (`DisconnectResponse`,
`SyncResponse`). Low priority but improves OpenAPI documentation.

### 2.10 `sync_strava` ignores power thresholds

`backend/app/services/sync.py:67-83`

`power_thresholds` is initialized to `[]` but never populated from the context. If the user
has power zones configured, they won't be used for Strava stream-based zone computation.

**Fix:** Load power zone boundaries from `RunnerProfile` alongside HR and pace thresholds.

### 2.11 `dump_zones` silently swallows all exceptions

`backend/app/services/activities.py:37-45`

```python
except Exception:
    return None
```

If zone data is corrupted, this silently returns `None` with no log message.

**Fix:** Add `logger.warning("Failed to serialize zones: %s", e)` before returning `None`.

---

## Priority 3: Frontend Type Safety

### 3.1 Define `Split` interface

`frontend/src/types/schema.ts:159` — `splits: Record<string, any>[] | null`

The split data has a known shape (`averageSpeed`, `distance`, `averageHR`, `movingTime`,
`paceZone`, etc.). Currently untyped.

**Fix:** Define a `Split` interface in `schema.ts` and replace `Record<string, any>[]`.

### 3.2 Define `CustomZones` interfaces

`frontend/src/types/wizard.ts:157,239` — `custom_zones: Record<string, any>`

This flows through `useWizard`, `StepAthleteProfile`, and the API. Define `CustomZones`,
`HrZoneInput`, `PaceZoneInput`, `PowerZoneInput` interfaces.

### 3.3 Remove `FeatureFlags` index signature

`frontend/src/types/schema.ts:174` — `[key: string]: boolean`

This makes the type essentially `Record<string, boolean>`, defeating the purpose of the named
`isSwimmingEnabled` property. Any typo compiles without error.

**Fix:** Remove the index signature. Add named properties as flags are created.

### 3.4 Type API return values

`frontend/src/lib/api.ts` — lines 47, 66, 71, 76, 81, 86 return `Promise<any>`.

**Fix:** Define response types for `createPlan`, `activatePlan`, `deletePlan`, `updateWeek`,
`updateWorkout`, `createWorkout`. Move `PlanMeta` and `StravaStatus` from `api.ts` to
`types/`.

### 3.5 Use `unknown` in catch blocks

`frontend/src/hooks/useWizard.ts:278,298` — `catch (err: any)`.
`frontend/src/components/IntegrationsMenu.tsx:93` — `(error as any).response?.data?.detail`.

**Fix:** Use `unknown` and narrow. Extract a shared `extractApiError(err: unknown): string`
utility.

### 3.6 Fix uncontrolled pace zone inputs

`frontend/src/components/wizard/StepAthleteProfile.tsx:447`

Custom zone pace inputs use `defaultValue` (uncontrolled) instead of `value`. If profile
defaults arrive after mount (e.g., user connects Strava), the inputs show stale empty values.

**Fix:** Switch to controlled inputs with `value` and `onChange`.

### 3.7 Fix `isPool` evaluation for "No Event"

`frontend/src/components/wizard/StepSportEvent.tsx:26`

`SwimmingPoolEvents.includes('none')` is true (wizard.ts line 41 includes `'none'` in the
array), so `isPool` evaluates to true when "No Event" is selected for swimming. Pool/OW
badges display incorrectly.

**Fix:** Add `&& data.event_type !== 'none'` to the `isPool` check, or remove `'none'` from
`SwimmingPoolEvents`.

---

## Priority 4: Frontend Duplication

### 4.1 Extract `useSyncMutations()` hook

Sync mutation definitions are copy-pasted between:
- `frontend/src/components/RecentActivities.tsx:42-54`
- `frontend/src/components/WeekStats.tsx:38-50`

**Fix:** Create `frontend/src/hooks/useSyncMutations.ts` returning `{ garminSync, stravaSync }`.

### 4.2 Extract `useIntegrationStatus()` hook

`useStravaStatus()` + `useGarminToken()` + priority logic repeated in:
- `RecentActivities.tsx`
- `WeekStats.tsx`
- `PlanWizard.tsx`
- `IntegrationsMenu.tsx`

**Fix:** Create `useIntegrationStatus()` returning
`{ stravaConnected, garminConnected, preferredSource, canSync }`.

### 4.3 Extract `useStravaErrorToast()` hook

Strava error toast from URL params duplicated between:
- `frontend/src/components/IntegrationsMenu.tsx:52-61`
- `frontend/src/components/StravaSettings.tsx:22-32`

### 4.4 Consolidate Strava brand color

Hardcoded `#FC4C02` in 3+ files. Add to Tailwind config:

```js
// tailwind.config.js
colors: {
  strava: '#FC4C02',
}
```

### 4.5 Remove or deprecate `StravaSettings.tsx`

`frontend/src/components/StravaSettings.tsx` appears to be superseded by
`IntegrationsMenu.tsx` which handles both Strava and Garmin. If `StravaSettings` is no longer
imported anywhere, remove it. If it is, consolidate.

---

## Priority 5: Test Gaps

### 5.1 Backend test improvements

- `test_feature_flag_api.py:87-93` -- `_set_user_types` helper defined but never called
  (dead test code).
- `test_feature_flag_api.py:155-211` -- `TestRequireRole` methods manually set up
  engine/overrides in each method; refactor to use fixtures.
- `test_wizard_defaults.py:142,187,225` -- `RunnerProfile.user_id != None` selects ALL
  profiles; filter by known `user_id` instead.
- Missing: test for `set_flag` with empty/invalid flag names.
- Missing: test for malformed `training_zones_json` in wizard defaults endpoint.

### 5.2 Frontend test improvements

- `StepSportEvent.test.tsx` -- uses `toBeDefined()` instead of `toBeInTheDocument()` on
  `getByText()` results. The assertion is redundant (getByText throws on miss).
- Missing: tests for `IntegrationsMenu`, `ActivityModal`, `WeekStats`, `useWizard`.
- Missing: tests for event type selection and event date/name onChange in `StepSportEvent`.
- Missing: tests for mutation error paths (sync failures, API errors).
- Missing: `formatPace` test for negative values.
- Missing: `formatZoneRange` test for `0` boundary.

---

## Priority 6: Minor Improvements (Nice-to-Have)

### 6.1 Backend

- `strava.py:604` -- Log unknown sport types instead of silently converting.
- `strava.py:746-766` -- HR zone and power zone mapping blocks are nearly identical; extract
  helper.
- `strava.py:126-134` -- URL-encode `redirect_uri` parameter.
- `activities.py:125` -- `dump_zones(act.splits)` is semantically misleading; rename or add
  a `dump_json` alias.
- `routers/strava.py:26` -- `_WEBHOOK_SECRET` read at module import time; won't pick up
  env changes in tests.
- `routers/strava.py:59` -- `verify_state_token` imported inside function body but
  `StravaService` is already imported at module level from same module.
- `routers/activities.py:60-68` -- `/context.json` endpoint doesn't belong in the activities
  router.
- `routers/activities.py:71-76` -- Deprecated endpoint should use FastAPI's
  `deprecated=True` parameter.
- `schemas.py:451` -- `ActivitySchema.date` is `str` not `date`; no format validation.
- `schemas.py:365-367` -- `WeekUpdate.status` is unvalidated string.
- `deps.py:31-38` -- User email never updated if it changes in Keycloak.

### 6.2 Frontend

- `ActivityModal.tsx:137` -- Use `z.zoneNumber` as key instead of array index.
- `ActivityModal.tsx:103-104` -- Zone field fallback aliases (`zoneLow ?? zoneLowBoundary`)
  should be normalized at data ingestion.
- `PlanWizard.tsx:105,113` -- `sessionStorage.setItem('wizardInput', ...)` is fragile; stale
  data persists across navigations.
- `PlanWizard.tsx:91` -- `isManualMode` is a complex inline boolean; extract to
  `useWizard` as a derived property.
- `useWizard.ts:125-126,138-139` -- `eslint-disable` on `useMemo` deps should explain WHY.
- `useWizard.ts:308-319` -- `reset()` reverts to hardcoded defaults, not profile defaults.
- `AppShell.tsx` -- File exports `AppBrand`, `AppDescription`, `AppFooter` but no "shell";
  rename to `BrandComponents.tsx`.
- `privacy.tsx:10` -- `useAuth()` triggers re-renders; isolate to a child component.
- `privacy.tsx:22` -- Hardcoded "February 2026" date.
- `StepAthleteProfile.tsx` -- 463 lines; extract zone editor into `ZoneEditor` component.
- Accessibility: Modal missing `role="dialog"`, `aria-modal`, Escape-to-close. Dropdown
  missing `role="menu"`, `aria-expanded`, keyboard navigation. Form inputs missing `<label>`
  associations.

---

## Implementation Sequence

Recommended order for incremental implementation:

1. **Security fixes** (1.1-1.4) -- single commit, deploy immediately.
2. **Backend code quality** (2.1-2.3) -- highest-impact cleanups.
3. **Frontend type safety** (3.1-3.5, 3.6-3.7) -- tighten types, fix latent bugs.
4. **Frontend deduplication** (4.1-4.5) -- extract shared hooks.
5. **Remaining backend cleanup** (2.4-2.11) -- schema renames, response models, etc.
6. **Test improvements** (5.1-5.2) -- fill coverage gaps.
7. **Nice-to-haves** (6.1-6.2) -- as time allows.

Each priority group can be a single PR. Run `cd backend && uv run pytest` (336 tests) and
`cd frontend && npm run build` after each group to verify no regressions.
