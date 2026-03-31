# Strava Integration

Status: Implemented — PR #45.

## Overview

Strava provides an official OAuth2 API, making it a more reliable data source than the
unofficial Garmin Connect library. When a user connects Strava, their activity data is
fetched via the official API and takes precedence over any Garmin-sourced record for the
same activity.

The integration mirrors the Garmin pattern where possible (same `ActivityService` upsert
path, same `ActualActivity` data model, same sync-button UX) but differs in three key
areas:

1. **Auth**: Standard OAuth2 authorization code flow — no credentials ever sent to the server.
2. **Token storage**: Refresh token persisted server-side in a dedicated `StravaToken` table.
3. **Precedence**: Strava data wins over Garmin for the same activity (matched by date + distance).

---

## Strava API App Setup (pre-requisite)

Before implementation, register an app at https://www.strava.com/settings/api.

Required settings:
- **Authorization Callback Domain**: your app domain (e.g. `yourdomain.com`)
- **Authorization Callback URL**: `https://yourdomain.com/strava/callback` (frontend route — NOT a backend endpoint)

This produces a `client_id` (integer) and `client_secret` (string). Add to Docker Compose env:

```
STRAVA_CLIENT_ID=<integer>
STRAVA_CLIENT_SECRET=<string>
STRAVA_REDIRECT_URI=https://yourdomain.com/strava/callback
```

OAuth scopes required: `activity:read_all,profile:read_all`.

---

## Data Model Changes

### New table: `strava_token`

One row per user. Stores the OAuth token bundle so the backend can refresh it automatically.

| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PK | |
| `user_id` | INTEGER FK → user | UNIQUE — one token per user |
| `athlete_id` | BIGINT | Strava's athlete ID |
| `access_token` | VARCHAR | Expires after 6 hours |
| `refresh_token` | VARCHAR | Long-lived; used to get new access token |
| `expires_at` | BIGINT | Unix epoch seconds |
| `scope` | VARCHAR | Default `activity:read_all,profile:read_all` |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | Updated on every token refresh |

### Changes to `actualactivity`

| New column | Type | Notes |
|-----------|------|-------|
| `source` | VARCHAR | `'garmin'` \| `'strava'` \| `'manual'`; default `'garmin'` for existing rows |
| `strava_activity_id` | BIGINT | Nullable; unique index (partial, where not null) |

The existing `activity_id` column remains as the Garmin activity ID. A partial unique index
on `strava_activity_id` prevents duplicate Strava imports.

---

## Migration

File: `backend/db/migrations/005_add_strava.sql`

```sql
-- 005_add_strava.sql
-- Adds StravaToken table and source/strava_activity_id columns to actualactivity.

CREATE TABLE IF NOT EXISTS strava_token (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id),
    athlete_id BIGINT NOT NULL,
    access_token VARCHAR NOT NULL,
    refresh_token VARCHAR NOT NULL,
    expires_at BIGINT NOT NULL,
    scope VARCHAR NOT NULL DEFAULT 'activity:read_all',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE actualactivity ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'garmin';
ALTER TABLE actualactivity ADD COLUMN IF NOT EXISTS strava_activity_id BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS uix_actualactivity_strava_id
    ON actualactivity(strava_activity_id)
    WHERE strava_activity_id IS NOT NULL;
```

---

## Backend

### New SQLModel models (database.py)

```python
class StravaToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    athlete_id: int
    access_token: str
    refresh_token: str
    expires_at: int          # Unix epoch seconds
    scope: str = Field(default="activity:read_all,profile:read_all")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

`ActualActivity` gains:
```python
source: str = Field(default="garmin")
strava_activity_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, unique=True, nullable=True))
```

### New service: `backend/app/services/strava.py`

`StravaService(session)` — all DB interactions scoped to the injected session.

| Method | Description |
|--------|-------------|
| `exchange_code(code) -> dict` | POST to Strava token endpoint; returns raw token dict |
| `save_token(user_id, token_data) -> StravaToken` | Upsert StravaToken row |
| `get_token(user_id) -> StravaToken \| None` | Fetch token for user |
| `refresh_if_needed(token) -> StravaToken` | If `expires_at - now < 300s`, refresh and save |
| `disconnect(user_id)` | Delete StravaToken row |
| `fetch_activities(access_token, start_date, end_date) -> list[ActualActivity]` | Paginate `GET /athlete/activities` with `after`/`before` epoch params |
| `fetch_activity_detail(access_token, activity_id) -> dict` | `GET /activities/{id}` — for laps and zones |
| `map_activity(raw, laps, zones) -> ActualActivity` | Maps Strava fields to `ActualActivity` dataclass |

**Strava → ActualActivity field mapping:**

| Strava field | ActualActivity field | Notes |
|---|---|---|
| `id` | `strava_activity_id` | |
| `name` | `name` | |
| `sport_type` | `type` | Normalised to lowercase (e.g. `Run` → `running`) |
| `start_date_local` | `date` | Date part only |
| `distance` | `distance_m` | Already in metres |
| `elapsed_time` | `duration_s` | Already in seconds |
| `average_speed` | `average_pace_m_s` | Already in m/s |
| `average_heartrate` | `average_hr` | |
| `max_heartrate` | `max_hr` | |
| `average_watts` | `average_power` | |
| `suffer_score` | `training_load` | Approximate equivalent |
| `calories` | `calories` | |
| laps from `/activities/{id}/laps` | `splits_json` | |
| zones from `/activities/{id}/zones` | `hr_zones_json` | |

`aerobic_te` and `anaerobic_te` have no Strava equivalent — stored as `None`.

### New API endpoints (routers/strava.py)

Note: The OAuth callback is handled entirely by the **frontend** (`/strava/callback` route), not the backend. The frontend extracts the `code` and `state` params from the redirect URL and POSTs them to the backend exchange endpoint.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/strava/auth-url` | user | Returns `{ url: str }` — the Strava OAuth URL |
| `POST` | `/api/strava/exchange` | user | Receives `{ code, state }` JSON body from frontend; exchanges code for token, saves it |
| `GET` | `/api/strava/status` | user | Returns `{ connected: bool, athlete_id: int \| null }` |
| `DELETE` | `/api/strava/disconnect` | user | Deletes StravaToken row |
| `POST` | `/api/integrations/strava/sync` | user | Syncs last N days; query param `?days=7` |

The frontend `/strava/callback` route receives the OAuth redirect, reads `?code=` and `?state=` from the URL, then calls `POST /api/strava/exchange` with a JSON body. On error, the frontend shows a toast. There is no server-side redirect.

### Token auto-refresh

Before every sync, `StravaService.refresh_if_needed()` is called. If the access token
expires within 5 minutes, it POSTs to `https://www.strava.com/oauth/token` with
`grant_type=refresh_token` and updates the `StravaToken` row. The sync then proceeds
with the fresh access token. This is transparent to the user.

---

## Precedence Logic (Deduplication)

When both Garmin and Strava are connected, the same real-world activity will appear in
both syncs. Deduplication runs inside `ActivityService.save_activities()`.

**Match criteria**: same `date` AND `distance_m` within 1% tolerance.

**Rules**:

1. When saving a Strava activity, check for an existing row with `source = 'garmin'` on
   the same date where `abs(existing.distance_m - new.distance_m) / new.distance_m < 0.01`.
2. If found, **replace** that row's data with the Strava data and set `source = 'strava'`.
   The `activity_id` (Garmin ID) is cleared; `strava_activity_id` is set.
3. When saving a Garmin activity, check for an existing row with `source = 'strava'` using
   the same match criteria. If found, **skip** — the Strava record wins.

This means:
- Running Garmin sync after Strava sync: Garmin records that already exist as Strava are silently skipped.
- Running Strava sync after Garmin sync: existing Garmin records are upgraded to Strava records.
- Either sync can run independently if only one integration is connected.

---

## Frontend

### New component: `StravaSettings.tsx`

Mirrors `GarminSettings.tsx`. Rendered in the header next to the Garmin gear icon.

**Disconnected state:**
- "Connect with Strava" button (Strava orange `#FC4C02` brand colour)
- Calls `GET /api/strava/auth-url` then does `window.location.href = url`
- No credentials ever entered — pure OAuth redirect

**Connected state:**
- Green connected badge showing Strava athlete name (from status endpoint)
- "Disconnect" button — calls `DELETE /api/strava/disconnect`

**On app load:**
- `useStravaStatus` hook reads `GET /api/strava/status` (React Query, 5 min stale)
- If `?strava_error=` is in the URL query string on mount, show a Sonner error toast

### Updated `RecentActivities.tsx`

- When Strava is connected: show "Scan via Strava" sync button
- When only Garmin is connected: existing "Scan for new runs" button unchanged
- When both are connected: show only the Strava button (Strava takes precedence)
- Activity table gains a small source indicator per row: `S` (Strava) or `G` (Garmin)

### New hook: `useStravaStatus.ts`

```ts
// Returns { connected: boolean, athleteId: number | null, isLoading: boolean }
// Backed by GET /api/strava/status via React Query
// staleTime: 5 minutes
```

### Frontend API calls (`lib/api.ts`)

| Function | HTTP call |
|----------|-----------|
| `getStravaAuthUrl()` | `GET /api/strava/auth-url` |
| `getStravaStatus()` | `GET /api/strava/status` |
| `disconnectStrava()` | `DELETE /api/strava/disconnect` |
| `syncStravaActivities(days)` | `POST /api/integrations/strava/sync?days={days}` |

---

## Implementation Sequence

1. **Migration** — `005_add_strava.sql`
2. **DB models** — `StravaToken` in `database.py`; add `source` + `strava_activity_id` to `ActualActivity`
3. **`StravaService`** — token exchange, refresh, fetch, map
4. **`ActivityService` updates** — source precedence logic in `save_activities()`
5. **API endpoints** — auth-url, callback, status, disconnect, sync
6. **`useStravaStatus` hook**
7. **`StravaSettings.tsx`**
8. **`RecentActivities.tsx`** updates — Strava sync button, source badges

---

## Zone Data: Strava vs Garmin

Understanding the differences between Strava and Garmin zone data is critical for choosing
the right data source and avoiding double-counting.

### Per-activity zone data (time-in-zone)

| Data type | Garmin | Strava |
|---|---|---|
| HR zones (time-in-zone) | `get_activity_hr_in_timezones()` — always available | `GET /activities/{id}/zones` — **Summit (paid) only**; falls back to Streams computation for free users |
| Pace zones (time-in-zone) | Computed from raw telemetry via `enrich_zones_with_telemetry()` | NOT provided; must be computed from `velocity_smooth` + `time` streams |
| Power zones (time-in-zone) | `connectapi(powerTimeInZones)` + telemetry | `GET /activities/{id}/zones` — **Summit only**; falls back to Streams for free users |

**Key conclusion**: Pace zones require stream computation for both sources. HR/power zones are
pre-computed for Strava Summit users only; for free Strava users the Streams API
(`GET /activities/{id}/streams?keys=time,heartrate,velocity_smooth,watts`) is required — the
same approach as Garmin's `enrich_zones_with_telemetry()`.

### Athlete zone boundaries (zone range definitions)

| Data | Garmin | Strava |
|---|---|---|
| HR zone boundaries | Calculated by us (Tanaka formula) | `GET /athlete/zones` — returns `HeartRateZoneRanges` with min/max bpm per zone |
| Power zone boundaries | Not available | `GET /athlete/zones` — returns `PowerZoneRanges` |

`GET /athlete/zones` requires the `profile:read_all` OAuth scope (see Scope Requirements
below). `HeartRateZoneRanges.custom_zones` indicates whether the athlete has set custom
zones in Strava; if `false`, the boundaries are Strava defaults and may not be meaningful
for seeding `RunnerProfile.training_zones_json`.

### Strava Summit caveat

`GET /activities/{id}/zones` is a **Strava Summit (paid subscription) feature**. For free
users the endpoint returns an empty array. The service must handle this gracefully:

```python
zones_raw = self.fetch_activity_zones(access_token, activity_id)
if not zones_raw:
    # Free user or no zone data — compute from streams if available, else store None
    zones_raw = self._compute_zones_from_streams(access_token, activity_id)
```

`DetailedActivity.splits_metric` contains a `pace_zone` integer per split (e.g. zone 1–5),
but this is a per-split zone number, not a time-in-zone distribution for the whole activity.
To derive a full pace zone time distribution from Strava, use
`GET /activities/{id}/streams?keys=time,velocity_smooth` and apply the same bucketing logic
as `enrich_zones_with_telemetry()` in `garmin.py`.

---

## Athlete Profile Import

Strava provides athlete data that can populate `RunnerProfile` fields currently unavailable
from any other source.

### `GET /athlete` — `DetailedAthlete` fields

| Strava field | `RunnerProfile` field | Notes |
|---|---|---|
| `weight` (float, kg) | `weight_kg` (if added) | Not currently in schema; worth adding |
| `sex` (`M`/`F`) | `gender` | Map `M` → `male`, `F` → `female` |
| `ftp` (int, watts) | No current field | Useful for power zone calculation |
| `measurement_preference` (`feet`/`meters`) | Display preference only | Not stored |
| `premium` / `summit` (bool) | Informs Summit feature availability | Store on `StravaToken` or check at sync time |

Fields **not** available from Strava (still require manual wizard input):
`age`, `height_cm`, `experience_level`, `pain_points_json`, `weekly_availability`,
`longest_recent_distance_m`.

### Profile import strategy

Profile data is imported **once at OAuth connect time** and on each manual sync. The rule is
**merge, never overwrite manually-entered data**:

1. At callback (code exchange): fetch `GET /athlete` and call `AthleteProfileImporter`.
2. `AthleteProfileImporter.merge(profile, strava_athlete)`:
   - Only sets a field if the current `RunnerProfile` value is `None` or the default sentinel
     (e.g. `gender = "unknown"`, `weight_kg = None`).
   - Never overwrites a value the user explicitly set in the wizard.
3. On subsequent syncs: re-import weight and ftp only (these can legitimately change over time).

### Importing athlete HR zone boundaries

If `GET /athlete/zones` returns `custom_zones: true`, import the HR zone boundaries into
`RunnerProfile.training_zones_json`, following the same zone schema as the Tanaka-derived
zones. This only fires if the user has set custom zones in Strava (i.e., the data is
meaningful). If `custom_zones: false`, skip — Strava's defaults are not calibrated to the
athlete.

---

## Scope Requirements (updated)

| Scope | Required for |
|---|---|
| `activity:read_all` | Reading private activities (list + detail), laps, streams, zones |
| `profile:read_all` | `GET /athlete` (weight, sex, ftp, summit flag), `GET /athlete/zones` (HR/power zone boundaries) |

The OAuth authorization URL must request both scopes:

```
scope=activity:read_all,profile:read_all
```

Update the `GET /api/strava/auth-url` response and the migration docs accordingly.
`StravaToken.scope` stores the granted scopes so the backend can check before calling
scope-gated endpoints.

---

## Streams API for Pace Zone Computation

When `GET /activities/{id}/zones` returns no pace zone data (always) or no HR/power zone
data (free users), fall back to the Streams API:

```
GET /activities/{id}/streams?keys=time,heartrate,velocity_smooth,watts
```

This returns arrays of the same length, one value per second of the activity. Apply the same
bucketing logic as `enrich_zones_with_telemetry()` in `garmin.py`:

1. Fetch the athlete's HR zone boundaries from `RunnerProfile.training_zones_json` (or from
   `GET /athlete/zones` if available).
2. Walk the `heartrate` array second-by-second; accumulate seconds into each zone bucket.
3. Repeat for `velocity_smooth` (pace zones) using the pace zone boundaries.
4. Return the same `hr_zones_json` / `pace_zones_json` structure as Garmin.

Rate limit note: the Streams API counts as one request per call. With a 100 req/15-min and
1000 req/day limit, fetching streams for every activity in a 30-day sync window is
feasible for most users (< 30 activities), but the service should skip stream fetches for
activities older than `STRAVA_STREAMS_MAX_AGE_DAYS` (default: 90 days) to protect the
daily quota.

---

## Data Conflict Resolution (full rules)

These rules extend the Precedence Logic section and make the merge behaviour explicit for
every data field.

### Activity-level conflicts (same real-world run in both Garmin and Strava)

Match criteria: same `date` AND `distance_m` within 1% tolerance.

| Field | Winner | Rationale |
|---|---|---|
| `name` | Strava | User-visible; Strava names are user-authored |
| `distance_m` | Strava | Official API; more accurate GPS processing |
| `duration_s` / `elapsed_time` | Strava | Same reason |
| `average_pace_m_s` | Strava | Derived from distance/time; consistent |
| `average_hr` / `max_hr` | Strava if available, else Garmin | Strava only if sensor data present |
| `average_power` | Strava if `average_watts` present, else Garmin | |
| `training_load` | Garmin | Garmin's Training Effect / Training Stress Score is richer than Strava's `suffer_score` |
| `aerobic_te` / `anaerobic_te` | Garmin only | No Strava equivalent |
| `calories` | Strava | Strava uses a more accurate metabolic model |
| `hr_zones_json` | Strava (Summit) or computed from streams | Strava Summit zones are pre-computed; otherwise derive from streams (same quality as Garmin) |
| `pace_zones_json` | Computed from streams (both sources identical) | Neither provides this directly |
| `splits_json` | Strava | Strava lap data is GPS-accurate |
| `strava_activity_id` | Strava | Set to Strava ID |
| `activity_id` (Garmin ID) | Cleared | Replaced by Strava record |
| `source` | `'strava'` | |

When a Garmin record is being upgraded to a Strava record, the merge writes all Strava
fields and preserves only `training_load`, `aerobic_te`, and `anaerobic_te` from the
original Garmin row (if not `None`).

### Profile-level conflicts (athlete profile data)

| Field | Priority | Rule |
|---|---|---|
| `gender` | Manual wizard > Strava | Only import from Strava if `RunnerProfile.gender` is `"unknown"` or `None` |
| `weight_kg` | Strava > wizard | Weight is factual and changes; always update from Strava on sync |
| HR zone boundaries | Manual wizard > Strava custom zones > Tanaka formula | Import Strava custom zones only if user has not manually set zones |
| FTP | Strava > nothing | No wizard field for FTP; always import if available |

---

## Resolved Decisions

- `STRAVA_REDIRECT_URI`: Points to the **frontend** `/strava/callback` route (e.g. `https://3h2os.com/strava/callback`). The frontend handles the redirect and POSTs the code to `POST /api/strava/exchange`.
- Strava sync triggers `recalculate_plan_progression`: **yes**, same as Garmin sync.
- `STRAVA_STREAMS_MAX_AGE_DAYS`: **90 days** (default). Skip stream fetches for activities older than 90 days to protect the daily API quota.
- `weight_kg` already exists on `RunnerProfile`. `ftp` added via migration `006_add_profile_strava_fields.sql`. Note: `strava_athlete_id` was planned but **not implemented** — it does not exist on `RunnerProfile` or in any migration.
