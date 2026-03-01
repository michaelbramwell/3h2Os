-- 004_add_feature_flags.sql
-- Adds user_types_json column to the user table and creates the featureflag
-- table for the feature flag system.

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS user_types_json VARCHAR DEFAULT '["standard"]';

CREATE TABLE IF NOT EXISTS featureflag (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    enabled_for_json VARCHAR NOT NULL DEFAULT '[]',
    description VARCHAR
);
