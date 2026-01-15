# 3h2Os Backend API

The backend for the 3h2Os project, built with FastAPI.

## Tech Stack
- **Framework:** FastAPI
- **Database:** SQLite (SQLModel)
- **Package Manager:** uv

## Getting Started

1. **Install Dependencies:**
   ```bash
   uv sync
   ```

2. **Run Server:**
   ```bash
   uv run uvicorn app.main:app --reload
   ```
   Access the API at `http://localhost:8000`.
   API Documentation: `http://localhost:8000/docs`.
