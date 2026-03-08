# Strava API Review Application — 3h2Os

Use this document to fill out the [Strava app review form](https://share.hsforms.com/1VXSwPUYqSH6IxK0y51FjHwcnkd8).

---

## App Name

3h2Os

## Website URL

https://3h2os.com

## App Description (short — 1–2 sentences)

3h2Os is a multi-sport training plan platform for self-coached amateur athletes training for running and swimming events. It generates personalised, periodised training plans and syncs with Strava to compare planned workouts against actual completed activities.

---

## Full Use Case Description

3h2Os helps amateur athletes — runners and swimmers — build and follow structured, periodised training programs leading up to a target race. The app generates a complete week-by-week plan across five phases (Base, Build, Peak, Taper, Race) based on the athlete's experience level, available training days, goal event, and personal bests.

Strava is used to pull in the athlete's completed activities so the app can compare planned workouts against actuals on a per-week dashboard. This gives athletes a clear picture of training adherence and helps them adjust future weeks based on what was actually done.

Specific Strava API usage:

- **OAuth2 connect flow** — athletes connect their Strava account once via the standard OAuth2 flow. Tokens are stored server-side and auto-refreshed; credentials never pass through the browser after the initial connect.
- **Activity sync** (`GET /athlete/activities`) — fetches recent activities (typically the last 7–30 days) to match against the training plan. Paginated using `after`/`before` epoch timestamps to avoid fetching unnecessary data.
- **Laps** (`GET /activities/{id}/laps`) — lap splits are displayed in the activity detail view so athletes can review pace distribution across an effort.
- **Streams** (`GET /activities/{id}/streams?keys=time,heartrate,velocity_smooth,watts`) — used to compute time-in-zone breakdowns (HR, pace, power) for activities within the last 90 days. Only fetched once per activity and cached in the database; never re-fetched.
- **Zones** (`GET /activities/{id}/zones`) — attempted first; streams are only used as a fallback if zone data is unavailable.
- **Athlete profile** (`GET /athlete`, `GET /athlete/zones`) — imported once on connect to pre-populate the athlete's weight, HR zone boundaries, and FTP into their training profile.
- **Webhooks** — implemented to receive real-time activity creation/update events, eliminating the need to poll for new activities.

The app is designed to be conservative with API usage: activities are cached after the first fetch, streams are only fetched within a 90-day window, and webhooks handle new activity ingestion to avoid polling.

---

## Scopes Required

- `activity:read_all` — to read private activities, laps, and streams
- `profile:read_all` — to read athlete profile data and zone boundaries

---

## Expected Number of Athletes

Initially: 10–50 (early access / beta users)  
Growth target: several hundred within 12 months

---

## Does the app comply with Strava's API agreement and brand guidelines?

Yes. The app:
- Does not store or re-sell raw Strava data to third parties
- Displays Strava branding and connect buttons per the brand guidelines
- Implements webhook deauthorization handling to remove athlete data when a user disconnects
- Only requests the minimum scopes needed

---

## Additional Notes

The app currently has Garmin Connect integration live and Strava integration fully built and ready to launch. The 1-athlete limit is the only blocker to making Strava sync available to beta users. Rate limit usage is expected to be low per athlete given the caching and webhook strategy described above.
