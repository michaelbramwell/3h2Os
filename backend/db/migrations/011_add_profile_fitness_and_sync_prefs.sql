-- Add fitness metrics and per-source sync preferences to runner_profile.
--
-- New columns:
--   resting_hr              Resting heart rate (bpm); sourced from Garmin
--   vo2max                  VO2Max estimate (ml/kg/min); sourced from Garmin
--   lactate_threshold_hr    Lactate threshold heart rate (bpm); sourced from Garmin
--   lactate_threshold_pace  Lactate threshold pace (m/s); sourced from Garmin
--   profile_sync_prefs_json JSON object controlling which source may write each field.
--                           Schema:
--                           {
--                             "garmin": { "weight": true, "height": true,
--                                         "resting_hr": true, "vo2max": true,
--                                         "lactate_threshold": true },
--                             "strava": { "weight": false, "ftp": true, "hr_zones": true }
--                           }
--                           NULL means "use defaults" (all enabled, Garmin wins for shared fields).
--   profile_last_synced_at  ISO timestamp of the most recent successful profile sync (any source).

ALTER TABLE runnerprofile
    ADD COLUMN IF NOT EXISTS resting_hr INTEGER DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS vo2max FLOAT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS lactate_threshold_hr INTEGER DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS lactate_threshold_pace FLOAT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS profile_sync_prefs_json TEXT DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS profile_last_synced_at TIMESTAMP DEFAULT NULL;
