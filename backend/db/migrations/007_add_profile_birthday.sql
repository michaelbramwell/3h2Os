-- 007_add_profile_birthday.sql
-- Adds birthday column to runnerprofile so age can be kept current from Strava/Garmin.
-- Also adds garmin_synced_at to track when Garmin profile data was last imported.

ALTER TABLE runnerprofile ADD COLUMN IF NOT EXISTS birthday DATE;
