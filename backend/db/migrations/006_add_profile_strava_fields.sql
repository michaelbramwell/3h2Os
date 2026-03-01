-- 006_add_profile_strava_fields.sql
-- Adds ftp column to runnerprofile for power zone calculation from Strava data.

ALTER TABLE runnerprofile ADD COLUMN IF NOT EXISTS ftp INTEGER;
