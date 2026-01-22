# 3h2Os Backend API

The backend for the 3h2Os project, built with FastAPI.

## Tech Stack
- **Framework:** FastAPI
- **Database:** PostgreSQL (Production/Docker)
- **Auth:** Keycloak (OIDC/JWT)
- **ORM:** SQLModel (SQLAlchemy + Pydantic)
- **Migrations:** Alembic
- **Package Manager:** uv

## Running Locally

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run Migrations (Initial Setup):**
   ```bash
   uv run alembic upgrade head
   ```

3. **Run Server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   - Access the API at `http://localhost:8000`.
   - API Documentation: `http://localhost:8000/docs`.
   - **Note:** The API is protected by Keycloak. You will need a valid JWT token to access endpoints.

4. **JWT Authentication Configuration (Local Dev):**
   The application uses RS256 for JWT signature verification. For local development, you need to generate a key pair in the `certs/` directory:
   
   ```bash
   # From project root
   mkdir -p certs
   openssl genrsa -out certs/private_key.pem 2048
   openssl rsa -in certs/private_key.pem -pubout -out certs/public_key.pem
   ```

   Then, point the application to the public key:
   ```bash
   export JWT_PUBLIC_KEY_PATH=$(pwd)/../certs/public_key.pem
   uv run uvicorn app.main:app --reload
   ```
   If this environment variable is not set, the app may disable signature verification in development mode (with a warning).

## Running with Docker (PostgreSQL)

This project includes a Docker composition that runs the API alongside a PostgreSQL database and Keycloak.

1. **Start Services:**
   ```bash
   # Run from the project root directory
   docker compose up --build
   ```
   This will:
   - Start a PostgreSQL 15 container.
   - Start Keycloak for authentication.
   - Build the FastAPI app image.
   - Automatically run migrations (`alembic upgrade head`) on startup.
   - Expose the API at `http://localhost:8000`.

2. **Environment Configuration:**
   - The app detects the `DATABASE_URL` environment variable.
   - Keycloak settings are configured via `KEYCLOAK_*` env vars.

## Migrations

Managing database schema changes:

- **Create a new migration:**
  ```bash
  uv run alembic revision --autogenerate -m "Description of change"
  ```
- **Apply migrations:**
  ```bash
  uv run alembic upgrade head
  ```

