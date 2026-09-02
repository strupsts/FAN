#!/usr/bin/env bash

fan_stage_database() {
  local health_status
  local attempt

  docker compose -f "${FAN_REPO_ROOT}/docker-compose.yml" config --quiet
  docker compose -f "${FAN_REPO_ROOT}/docker-compose.yml" pull db
  docker compose -f "${FAN_REPO_ROOT}/docker-compose.yml" up -d db

  for attempt in $(seq 1 30); do
    health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' fan_postgres 2>/dev/null || true)"
    if [[ "${health_status}" == "healthy" ]]; then
      break
    fi
    if [[ "${health_status}" == "unhealthy" || "${health_status}" == "exited" || "${health_status}" == "dead" ]]; then
      echo "PostgreSQL container entered state: ${health_status}" >&2
      docker compose -f "${FAN_REPO_ROOT}/docker-compose.yml" logs --tail 40 db >&2
      return 1
    fi
    sleep 2
  done

  [[ "${health_status}" == "healthy" ]] || {
    echo "PostgreSQL did not become healthy within 60 seconds." >&2
    return 1
  }

  echo "Applying forward-only Alembic migrations. Existing data and volumes are preserved."
  (cd "${FAN_BACKEND_DIR}" && PYTHONPATH=. .venv/bin/alembic upgrade head)
}
