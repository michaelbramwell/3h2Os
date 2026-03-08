-- 007_add_profile_birthday.sql
-- Adds birthday column to runnerprofile so age can be kept current from Strava/Garmin.

ALTER TABLE runnerprofile ADD COLUMN IF NOT EXISTS birthday DATE;
