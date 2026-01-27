#!/bin/bash
set -e

# Configuration
MOUNT_POINT="/mnt/HC_Volume_104483418"
PROJECT_NAME="app"

echo "Stopping containers..."
docker compose -f docker-compose.prod.yml down

echo "Creating directory structure on $MOUNT_POINT..."
sudo mkdir -p "$MOUNT_POINT/postgres_data"
sudo mkdir -p "$MOUNT_POINT/backend_data"
sudo mkdir -p "$MOUNT_POINT/caddy_data"
sudo mkdir -p "$MOUNT_POINT/caddy_config"

echo "Migrating PostgreSQL data..."
# Use a temporary alpine container to copy data while preserving permissions
# We check if volume exists first to avoid errors on fresh installs
if docker volume inspect ${PROJECT_NAME}_postgres_data >/dev/null 2>&1; then
    docker run --rm \
      -v ${PROJECT_NAME}_postgres_data:/from \
      -v $MOUNT_POINT/postgres_data:/to \
      alpine sh -c "cp -av /from/. /to/"
else
    echo "Postgres data volume not found (fresh install?), skipping copy."
fi

echo "Migrating Backend data..."
if docker volume inspect ${PROJECT_NAME}_backend_data >/dev/null 2>&1; then
    docker run --rm \
      -v ${PROJECT_NAME}_backend_data:/from \
      -v $MOUNT_POINT/backend_data:/to \
      alpine sh -c "cp -av /from/. /to/"
else
    echo "Backend data volume empty or missing, skipping."
fi

echo "Migrating Caddy data..."
if docker volume inspect ${PROJECT_NAME}_caddy_data >/dev/null 2>&1; then
    docker run --rm \
      -v ${PROJECT_NAME}_caddy_data:/from \
      -v $MOUNT_POINT/caddy_data:/to \
      alpine sh -c "cp -av /from/. /to/"
fi

if docker volume inspect ${PROJECT_NAME}_caddy_config >/dev/null 2>&1; then
    docker run --rm \
      -v ${PROJECT_NAME}_caddy_config:/from \
      -v $MOUNT_POINT/caddy_config:/to \
      alpine sh -c "cp -av /from/. /to/"
fi

echo "Migration complete. Please check permissions in $MOUNT_POINT if necessary."
