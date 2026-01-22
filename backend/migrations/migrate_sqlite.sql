INSERT INTO runnerplan (title, is_active, created_at, plan_json, user_id) SELECT title, is_active, created_at, plan_json, user_id FROM sqlite_db.runnerplan;
