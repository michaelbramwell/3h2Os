INSERT INTO featureflag (name, enabled_for_json, description)
SELECT 'isAiEnabled', '[]', 'Controls AI-assisted plan generation in the wizard. Disabled - AI feature not yet released.'
WHERE NOT EXISTS (SELECT 1 FROM featureflag WHERE name = 'isAiEnabled');