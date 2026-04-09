
# 3h2Os Project Rules

## Tech Stack
- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **Backend:** FastAPI + Python 3.13
- **Database:** PostgreSQL (via SQLModel/SQLAlchemy)
- **Auth:** Keycloak (OIDC/JWT)
- **Tooling:** uv (Python), npm (Node), Docker

## Architecture
- **Auth:** All API endpoints are protected via `verify_jwt_middleware`.
  - **Verification:** Validates Keycloak JWTs using RS256. Public keys are fetched dynamically from the Keycloak JWKS endpoint at runtime — no static key file.
  - **Dev bypass:** `DEFAULT_USERNAME` env var + `ENVIRONMENT=development` allows unauthenticated local requests to resolve to a known user. Both conditions must be true.
- **Database:** Uses PostgreSQL for all environments. Schema changes are managed via custom forward-only SQL migrations in `db/migrations/` using `db/migrate.py`.
- **API:** RESTful API with Pydantic schemas.
- **Validation:** Guardrails logic in `backend/app/core/validation.py` (`ValidationEngine` class) runs inline on every workout save/update. The legacy script `backend/scripts/reflect_and_validate.py` exists as a CLI tool but is not the canonical path.

## Development Workflow
1. **Backend:**
   - Run `uv sync` to install deps.
   - Run `uv run uvicorn app.main:app --reload` to start dev server.
   - Run `uv run pytest` for tests.
2. **Frontend:**
   - Run `npm install`
   - Run `npm run dev`
3. **Database:**
   - Use `uv run python -m db.migrate` to apply migrations.
   - New migrations are plain SQL files in `db/migrations/`, numbered `NNN_description.sql`.

## Key Files
- `backend/app/main.py`: App entry point.
- `backend/app/core/auth.py`: JWT validation logic (dynamic JWKS from Keycloak).
- `backend/app/core/database.py`: SQLModel models.
- `frontend/src/lib/auth.ts`: Frontend auth logic (if applicable).

## Operational Rules
- **Branding:** The project name is strictly "3h2os" (all lowercase except the '3'). Never use "3h2Os".
- **Commit Safety:** Do not commit changes without explicit user permission. Always present a summary of changes and ask for confirmation before running `git commit`.
