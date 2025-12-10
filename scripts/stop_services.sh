#!/usr/bin/env bash
set -euo pipefail

# Stops the Docker Compose stack (neo4j, api, worker, notebooks).
# Usage: ./scripts/stop_services.sh [down options...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker/docker-compose.yml"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but not found in PATH." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Docker Compose is required (docker compose plugin or docker-compose binary)." >&2
  exit 1
fi

echo "Stopping services with Docker Compose..."
"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" down "$@"
