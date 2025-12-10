#!/usr/bin/env bash
set -euo pipefail

# Starts Neo4j, API, worker, and notebooks via Docker Compose.
# Usage: ./scripts/start_services.sh [api_port]

API_PORT="${1:-8000}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-7687}"
JUPYTER_PORT="${JUPYTER_PORT:-8888}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker/docker-compose.yml"
BUILD_HASH_FILE="${ROOT_DIR}/.docker-build-hash"

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

export API_PORT
export NEO4J_HTTP_PORT NEO4J_BOLT_PORT JUPYTER_PORT

# Check port availability (best-effort)
check_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i :"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
      return 1
    fi
  fi
  return 0
}

pick_free_port() {
  local desired=$1
  local fallback_start=$2
  if check_port "${desired}"; then
    echo "${desired}"
    return
  fi
  local candidate=$fallback_start
  while ! check_port "${candidate}"; do
    candidate=$((candidate + 1))
    if [ "${candidate}" -gt $((fallback_start + 100)) ]; then
      echo "Unable to find free port starting from ${fallback_start}" >&2
      exit 1
    fi
  done
  echo "${candidate}"
}

NEO4J_HTTP_PORT="$(pick_free_port "${NEO4J_HTTP_PORT}" 8500)"
NEO4J_BOLT_PORT="$(pick_free_port "${NEO4J_BOLT_PORT}" 8600)"
API_PORT="$(pick_free_port "${API_PORT}" 8100)"
JUPYTER_PORT="$(pick_free_port "${JUPYTER_PORT}" 8900)"

# Determine whether we need to rebuild images (changes or missing images).
compute_build_hash() {
  # Hash the Docker build context while skipping common caches.
  tar -C "${ROOT_DIR}" \
    --exclude='.git' \
    --exclude='.docker-build-hash' \
    --exclude='.venv' \
    --exclude='.DS_Store' \
    --exclude='**/__pycache__' \
    --exclude='**/.pytest_cache' \
    --exclude='**/node_modules' \
    --exclude='vision/H3LIXVision/.build' \
    --exclude='vision/H3LIXVision/.swiftpm' \
    --exclude='vision/H3LIXVision/DerivedData' \
    --exclude='datasets' \
    --exclude='results' \
    --exclude='analysis' \
    --exclude='AppIcons' \
    --exclude='AppIcons.zip' \
    --exclude='quest' \
    --exclude='*.log' \
    --exclude='*.tmp' \
    -cf - . | shasum | awk '{print $1}'
}

need_build=0
current_hash="$(compute_build_hash)"
if [ "${FORCE_BUILD:-0}" != "0" ]; then
  need_build=1
elif [ ! -f "${BUILD_HASH_FILE}" ] || [ "$(cat "${BUILD_HASH_FILE}")" != "${current_hash}" ]; then
  need_build=1
else
  # Ensure required images exist even if hash matches.
  for image in docker-api docker-worker docker-notebooks; do
    if ! docker image inspect "${image}" >/dev/null 2>&1; then
      need_build=1
      break
    fi
  done
fi

if [ "${need_build}" -eq 1 ]; then
  echo "Changes detected or images missing; building Docker images..."
  "${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" build
  echo "${current_hash}" > "${BUILD_HASH_FILE}"
else
  echo "No changes detected; reusing existing images (set FORCE_BUILD=1 to override)."
fi

echo "Starting services with Docker Compose (API_PORT=${API_PORT}, NEO4J_HTTP_PORT=${NEO4J_HTTP_PORT}, NEO4J_BOLT_PORT=${NEO4J_BOLT_PORT}, JUPYTER_PORT=${JUPYTER_PORT})..."
"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" up -d

echo
"${COMPOSE_CMD[@]}" -f "${COMPOSE_FILE}" ps
echo
echo "Neo4j browser: http://localhost:${NEO4J_HTTP_PORT}"
echo "Bolt:          bolt://localhost:${NEO4J_BOLT_PORT}"
echo "API:           http://localhost:${API_PORT}"
echo "Jupyter:       http://localhost:${JUPYTER_PORT}"
