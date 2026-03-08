INSERT INTO featureflag (name, enabled_for_json, description)
SELECT 'isSwimmingEnabled', '[]', 'Controls visibility of swimming plans and UI across the app.'
WHERE NOT EXISTS (SELECT 1 FROM featureflag WHERE name = 'isSwimmingEnabled');
