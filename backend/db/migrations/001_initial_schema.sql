-- 001_initial_schema.sql
-- Consolidated from Alembic migrations a2f1813ebffc through b4e2a1c93f7d.
-- Represents the full schema as of 2026-02-10.

CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS runnerplan (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    type VARCHAR NOT NULL DEFAULT 'running',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    plan_json TEXT NOT NULL DEFAULT '[]',
    user_id INTEGER REFERENCES "user"(id)
);

CREATE TABLE IF NOT EXISTS planweek (
    id SERIAL PRIMARY KEY,
    plan_id INTEGER NOT NULL REFERENCES runnerplan(id),
    start_date DATE NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'normal'
);

CREATE TABLE IF NOT EXISTS planworkout (
    id SERIAL PRIMARY KEY,
    week_id INTEGER NOT NULL REFERENCES planweek(id),
    date DATE NOT NULL,
    day_name VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    activity_type VARCHAR NOT NULL DEFAULT 'Run',
    workout_format VARCHAR,
    distance_m FLOAT NOT NULL DEFAULT 0.0,
    time_of_day VARCHAR NOT NULL DEFAULT 'AM'
);

CREATE TABLE IF NOT EXISTS actualactivity (
    id SERIAL PRIMARY KEY,
    activity_id BIGINT UNIQUE,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    date DATE NOT NULL,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL,
    distance_m FLOAT NOT NULL,
    duration_s FLOAT NOT NULL,
    average_pace_m_s FLOAT,
    average_hr FLOAT,
    max_hr FLOAT,
    average_power FLOAT,
    aerobic_te FLOAT,
    anaerobic_te FLOAT,
    training_load FLOAT,
    calories FLOAT,
    hr_zones_json TEXT,
    pace_zones_json TEXT,
    power_zones_json TEXT,
    splits_json TEXT
);

CREATE TABLE IF NOT EXISTS runnerprofile (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    age INTEGER NOT NULL,
    gender VARCHAR NOT NULL,
    height_cm INTEGER NOT NULL,
    training_zones_json TEXT,
    swim_zones_json TEXT,
    fueling_json TEXT,
    weight_kg FLOAT,
    experience_level VARCHAR,
    events_completed_json TEXT,
    pain_points_json TEXT,
    weekly_availability INTEGER,
    longest_recent_distance_m INTEGER
);

CREATE TABLE IF NOT EXISTS runnerproject (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    name VARCHAR NOT NULL DEFAULT 'My Project',
    goal VARCHAR NOT NULL,
    event VARCHAR NOT NULL,
    event_date DATE NOT NULL,
    event_type VARCHAR,
    target_time VARCHAR,
    primary_goal VARCHAR
);

CREATE TABLE IF NOT EXISTS plantemplate (
    id SERIAL PRIMARY KEY,
    sport VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    level VARCHAR NOT NULL,
    default_weeks INTEGER NOT NULL DEFAULT 14,
    structure_json TEXT NOT NULL
);
