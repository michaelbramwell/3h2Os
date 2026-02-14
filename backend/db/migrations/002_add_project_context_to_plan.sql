-- 002_add_project_context_to_plan.sql
-- Snapshot event/goal/event_date on each plan so activate_plan can
-- restore the sidebar context when switching between plans.

ALTER TABLE runnerplan ADD COLUMN IF NOT EXISTS event VARCHAR;
ALTER TABLE runnerplan ADD COLUMN IF NOT EXISTS goal VARCHAR;
ALTER TABLE runnerplan ADD COLUMN IF NOT EXISTS event_date DATE;
