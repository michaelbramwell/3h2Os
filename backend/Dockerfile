# Stage 1: Build frontend assets
FROM node:20-slim AS frontend-builder
WORKDIR /src
COPY app/static/package.json app/static/tsconfig.json ./app/static/
COPY app/static/ts ./app/static/ts
WORKDIR /src/app/static
# Install dependencies and build via tsc
RUN npm install && npm run build


# Stage 2: Application Runner
FROM python:3.13-slim-bookworm

# Install uv via pip to avoid GHCR auth issues
RUN pip install uv

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into the virtual environment
RUN uv sync --frozen --no-dev

# Copy application source code
COPY . .

# Copy built frontend assets from the builder stage
COPY --from=frontend-builder /src/app/static/js ./app/static/js

# Create the data directory (expected by database.py default)
RUN mkdir -p data

# Expose the application port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
