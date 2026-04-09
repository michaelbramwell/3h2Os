CREATE TABLE IF NOT EXISTS activityshare (
  id SERIAL PRIMARY KEY,
  activity_id INTEGER NOT NULL REFERENCES actualactivity(id) ON DELETE CASCADE,
  token VARCHAR(64) NOT NULL UNIQUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activityshare_token ON activityshare(token);
CREATE INDEX IF NOT EXISTS idx_activityshare_activity_id ON activityshare(activity_id);
