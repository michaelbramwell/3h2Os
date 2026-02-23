-- 003_add_wizard_input_to_plan.sql
-- Store the wizard input JSON on each plan so the wizard can be re-opened
-- in edit mode to modify and regenerate the plan.

ALTER TABLE runnerplan ADD COLUMN IF NOT EXISTS wizard_input_json TEXT;
