INSERT INTO featureflag (name, enabled_for_json, description)
SELECT 'isGarminEnabled', '[]', 'Controls visibility and access to Garmin integration (connect, sync, Training Effect). Disabled by default due to IP rate-limiting issues with the unofficial Garmin API.'
WHERE NOT EXISTS (SELECT 1 FROM featureflag WHERE name = 'isGarminEnabled');
