-- Creates the keycloak database if it does not already exist.
-- Mounted into /docker-entrypoint-initdb.d/ by docker-compose so Postgres
-- runs it automatically on first startup.
SELECT 'CREATE DATABASE keycloak'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec
