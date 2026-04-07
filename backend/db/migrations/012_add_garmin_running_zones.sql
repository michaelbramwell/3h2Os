-- Add garmin_running_zones_json to runnerprofile.
-- Stores pace zones fetched directly from Garmin Connect user-settings,
-- which is the highest-priority source for training pace zones.
ALTER TABLE runnerprofile
    ADD COLUMN IF NOT EXISTS garmin_running_zones_json TEXT;
