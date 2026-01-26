
# 3h2Os Project Rules

## Tech Stack
- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **Backend:** FastAPI + Python 3.13
- **Database:** PostgreSQL (via SQLModel/SQLAlchemy)
- **Auth:** Keycloak (OIDC/JWT)
- **Tooling:** uv (Python), npm (Node), Docker

## Architecture
- **Auth:** All API endpoints are protected via `verify_jwt_middleware`.
  - **Verification:** Validates Keycloak JWTs using RS256 public keys.
  - **Configuration:** Uses `JWT_PUBLIC_KEY_PATH` (pointing to `certs/public_key.pem`) or fetches from IdP (future).
- **Database:** Uses PostgreSQL for all environments. Schema changes are managed via Alembic.
- **API:** RESTful API with Pydantic schemas. 
- **Validation:** "Guardrails" logic in `reflect_and_validate.py` ensures training safety.

## Development Workflow
1. **Backend:**
   - Run `uv sync` to install deps.
   - Run `uv run uvicorn app.main:app --reload` to start dev server.
   - Run `uv run pytest` for tests.
2. **Frontend:**
   - Run `npm install`
   - Run `npm run dev`
3. **Database:**
   - Use `uv run alembic upgrade head` to apply migrations.

## Key Files
- `backend/app/main.py`: App entry point.
- `backend/app/core/auth.py`: JWT validation logic.
- `backend/app/core/database.py`: SQLModel models.
- `frontend/src/lib/auth.ts`: Frontend auth logic (if applicable).

## Operational Rules
- **Commit Safety:** Do not commit changes without explicit user permission. Always present a summary of changes and ask for confirmation before running `git commit`.
