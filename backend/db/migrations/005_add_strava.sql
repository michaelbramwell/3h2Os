-- 005_add_strava.sql
-- Adds StravaToken table and source/strava_activity_id columns to actualactivity.

CREATE TABLE IF NOT EXISTS strava_token (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES "user"(id),
    athlete_id BIGINT NOT NULL,
    access_token VARCHAR NOT NULL,
    refresh_token VARCHAR NOT NULL,
    expires_at BIGINT NOT NULL,
    scope VARCHAR NOT NULL DEFAULT 'activity:read_all,profile:read_all',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

ALTER TABLE actualactivity ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'garmin';
ALTER TABLE actualactivity ADD COLUMN IF NOT EXISTS strava_activity_id BIGINT;

CREATE UNIQUE INDEX IF NOT EXISTS uix_actualactivity_strava_id
    ON actualactivity(strava_activity_id)
    WHERE strava_activity_id IS NOT NULL;
