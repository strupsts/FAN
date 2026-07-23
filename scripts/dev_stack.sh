#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

RUNTIME_DIR="${ROOT_DIR}/.runtime"
PID_DIR="${RUNTIME_DIR}/pids"
LOG_DIR="${RUNTIME_DIR}/logs"

API_PID_FILE="${PID_DIR}/api.pid"
VLM_PID_FILE="${PID_DIR}/vlm.pid"
FRONTEND_PID_FILE="${PID_DIR}/frontend.pid"
STOP_REQUEST_FILE="${RUNTIME_DIR}/stop-requested"

API_LOG_FILE="${LOG_DIR}/api.log"
VLM_LOG_FILE="${LOG_DIR}/vlm.log"
FRONTEND_LOG_FILE="${LOG_DIR}/frontend.log"

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
VLM_BASE_URL="${VLM_BASE_URL:-http://127.0.0.1:8002/v1}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://127.0.0.1:8100}"
VLM_API_KEY="${VLM_API_KEY:-local-dev-key}"

DB_STARTUP_TIMEOUT_SECONDS="${DB_STARTUP_TIMEOUT_SECONDS:-60}"
API_STARTUP_TIMEOUT_SECONDS="${API_STARTUP_TIMEOUT_SECONDS:-60}"
VLM_STARTUP_TIMEOUT_SECONDS="${VLM_STARTUP_TIMEOUT_SECONDS:-360}"
FRONTEND_STARTUP_TIMEOUT_SECONDS="${FRONTEND_STARTUP_TIMEOUT_SECONDS:-120}"

DB_STARTED_BY_SCRIPT=0
TAIL_PID=""


log() {
  printf '[dev] %s\n' "$*"
}


fail() {
  printf '[dev] ERROR: %s\n' "$*" >&2
  exit 1
}


compose() {
  docker compose \
    --project-directory "${ROOT_DIR}" \
    -f "${ROOT_DIR}/docker-compose.yml" \
    "$@"
}


read_pid_file() {
  local pid_file="$1"

  if [[ ! -f "${pid_file}" ]]; then
    return 1
  fi

  local pid
  pid="$(cat "${pid_file}")"

  if [[ ! "${pid}" =~ ^[0-9]+$ ]]; then
    return 1
  fi

  printf '%s\n' "${pid}"
}


pid_is_running() {
  local pid="$1"
  kill -0 "${pid}" 2>/dev/null
}


remove_stale_pid_file() {
  local pid_file="$1"
  local service_name="$2"

  local pid
  pid="$(read_pid_file "${pid_file}" 2>/dev/null || true)"

  if [[ -z "${pid}" ]]; then
    rm -f "${pid_file}"
    return
  fi

  if pid_is_running "${pid}"; then
    fail "${service_name} is already managed by dev stack with PID ${pid}. Run: make dev-down"
  fi

  rm -f "${pid_file}"
}


stop_process_group() {
  local pid_file="$1"
  local service_name="$2"

  local pid
  pid="$(read_pid_file "${pid_file}" 2>/dev/null || true)"

  if [[ -z "${pid}" ]]; then
    rm -f "${pid_file}"
    return
  fi

  if ! pid_is_running "${pid}"; then
    rm -f "${pid_file}"
    return
  fi

  log "Stopping ${service_name} (PID ${pid})..."

  # The service is started in its own session, so this stops its children too.
  kill -TERM -- "-${pid}" 2>/dev/null \
    || kill -TERM "${pid}" 2>/dev/null \
    || true

  for _ in $(seq 1 40); do
    if ! pid_is_running "${pid}"; then
      rm -f "${pid_file}"
      return
    fi

    sleep 0.25
  done

  log "${service_name} did not stop gracefully; forcing shutdown."

  kill -KILL -- "-${pid}" 2>/dev/null \
    || kill -KILL "${pid}" 2>/dev/null \
    || true

  rm -f "${pid_file}"
}


db_is_running() {
  [[ -n "$(compose ps --status running -q db 2>/dev/null)" ]]
}


wait_for_database() {
  local deadline=$((SECONDS + DB_STARTUP_TIMEOUT_SECONDS))

  log "Waiting for Postgres readiness..."

  while ((SECONDS < deadline)); do
    if compose exec -T db \
      pg_isready -U fan -d fan >/dev/null 2>&1; then
      log "Postgres is ready."
      return
    fi

    sleep 2
  done

  fail "Postgres did not become ready within ${DB_STARTUP_TIMEOUT_SECONDS}s."
}


wait_for_http() {
  local service_name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local service_pid="$4"
  local api_key="${5:-}"

  local deadline=$((SECONDS + timeout_seconds))

  log "Waiting for ${service_name} readiness..."

  while ((SECONDS < deadline)); do
    if ! pid_is_running "${service_pid}"; then
      log "${service_name} exited before becoming ready."
      return 1
    fi

    if [[ -n "${api_key}" ]]; then
      if curl -fsS \
        -H "Authorization: Bearer ${api_key}" \
        "${url}" >/dev/null 2>&1; then
        log "${service_name} is ready."
        return
      fi
    elif curl -fsS "${url}" >/dev/null 2>&1; then
      log "${service_name} is ready."
      return
    fi

    sleep 2
  done

  log "${service_name} did not become ready within ${timeout_seconds}s."
  return 1
}


check_requirements() {
  local command_name

  for command_name in docker curl setsid tail; do
    command -v "${command_name}" >/dev/null 2>&1 \
      || fail "Required command is missing: ${command_name}"
  done

  [[ -x "${ROOT_DIR}/backend/.venv/bin/uvicorn" ]] \
    || fail "Backend environment is missing. Run: make setup"

  local vlm_venv="${VLM_VENV:-${HOME}/.venvs/fan-vllm}"

  [[ -x "${vlm_venv}/bin/vllm" ]] \
    || fail "VLM environment is missing: ${vlm_venv}"

  [[ -s "${HOME}/.nvm/nvm.sh" ]] \
    || fail "nvm is missing. Install nvm before running the frontend."

  [[ -f "${ROOT_DIR}/frontend/package.json" ]] \
    || fail "Frontend project is missing."

  [[ -d "${ROOT_DIR}/frontend/node_modules" ]] \
    || fail "Frontend dependencies are missing. Run: cd frontend && npm install"
}


ensure_manual_services_are_stopped() {
  if curl -fsS "${API_BASE_URL}/health" >/dev/null 2>&1; then
    fail "API is already running outside dev stack. Stop it first."
  fi

  if curl -fsS \
    -H "Authorization: Bearer ${VLM_API_KEY}" \
    "${VLM_BASE_URL}/models" >/dev/null 2>&1; then
    fail "VLM is already running outside dev stack. Stop it first."
  fi

  if curl -fsS "${FRONTEND_BASE_URL}" >/dev/null 2>&1; then
    fail "Frontend is already running outside dev stack. Stop it first."
  fi
}


start_vlm() {
  : > "${VLM_LOG_FILE}"

  setsid bash -c '
    cd "$1"
    exec bash scripts/serve_vlm.sh
  ' _ "${ROOT_DIR}" >"${VLM_LOG_FILE}" 2>&1 &

  local pid=$!
  printf '%s\n' "${pid}" > "${VLM_PID_FILE}"

  log "VLM started with PID ${pid}."
}


start_api() {
  : > "${API_LOG_FILE}"

  setsid bash -c '
    cd "$1/backend"
    exec env \
      RECEIPT_EXTRACTION_PROVIDER=vlm \
      PYTHONPATH=. \
      .venv/bin/uvicorn app.main:app --reload
  ' _ "${ROOT_DIR}" >"${API_LOG_FILE}" 2>&1 &

  local pid=$!
  printf '%s\n' "${pid}" > "${API_PID_FILE}"

  log "API started with PID ${pid}."
}


start_frontend() {
  : > "${FRONTEND_LOG_FILE}"

  setsid bash -c '
    export NVM_DIR="${HOME}/.nvm"
    source "${NVM_DIR}/nvm.sh"

    cd "$1/frontend"
    nvm use --silent

    exec npm run start:mobile
  ' _ "${ROOT_DIR}" >"${FRONTEND_LOG_FILE}" 2>&1 &

  local pid=$!
  printf '%s\n' "${pid}" > "${FRONTEND_PID_FILE}"

  log "Frontend started with PID ${pid}."
}


start_log_stream() {
  tail -n +1 -F \
    "${VLM_LOG_FILE}" \
    "${API_LOG_FILE}" \
    "${FRONTEND_LOG_FILE}" &

  TAIL_PID=$!
}


cleanup_up() {
  local exit_code=$?

  trap - EXIT INT TERM

  if [[ -n "${TAIL_PID}" ]]; then
    kill "${TAIL_PID}" 2>/dev/null || true
  fi

  stop_process_group "${FRONTEND_PID_FILE}" "Frontend"
  stop_process_group "${API_PID_FILE}" "API"
  stop_process_group "${VLM_PID_FILE}" "VLM"
  rm -f "${STOP_REQUEST_FILE}"

  if ((DB_STARTED_BY_SCRIPT == 1)); then
    log "Stopping Postgres..."
    compose stop db >/dev/null 2>&1 || true
  fi

  log "Dev stack stopped."
  exit "${exit_code}"
}


action_up() {
  check_requirements

  mkdir -p "${PID_DIR}" "${LOG_DIR}"
  rm -f "${STOP_REQUEST_FILE}"

  remove_stale_pid_file "${API_PID_FILE}" "API"
  remove_stale_pid_file "${VLM_PID_FILE}" "VLM"
  remove_stale_pid_file "${FRONTEND_PID_FILE}" "Frontend"

  ensure_manual_services_are_stopped

  trap cleanup_up EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM

  if db_is_running; then
    log "Postgres is already running; reusing it."
  else
    log "Starting Postgres..."
    compose up -d db
    DB_STARTED_BY_SCRIPT=1
  fi

  wait_for_database

  log "Applying database migrations..."
  (
    cd "${ROOT_DIR}/backend"
    PYTHONPATH=. .venv/bin/alembic upgrade head
  )

  start_vlm
  start_api
  start_frontend
  start_log_stream

  local api_pid
  local vlm_pid
  local frontend_pid

  api_pid="$(cat "${API_PID_FILE}")"
  vlm_pid="$(cat "${VLM_PID_FILE}")"
  frontend_pid="$(cat "${FRONTEND_PID_FILE}")"

  wait_for_http \
    "API" \
    "${API_BASE_URL}/health" \
    "${API_STARTUP_TIMEOUT_SECONDS}" \
    "${api_pid}" \
    || fail "API startup failed. See: ${API_LOG_FILE}"

  wait_for_http \
    "Frontend" \
    "${FRONTEND_BASE_URL}" \
    "${FRONTEND_STARTUP_TIMEOUT_SECONDS}" \
    "${frontend_pid}" \
    || fail "Frontend startup failed. See: ${FRONTEND_LOG_FILE}"

  wait_for_http \
    "VLM" \
    "${VLM_BASE_URL}/models" \
    "${VLM_STARTUP_TIMEOUT_SECONDS}" \
    "${vlm_pid}" \
    "${VLM_API_KEY}" \
    || fail "VLM startup failed. See: ${VLM_LOG_FILE}"

  printf '\n'
  log "F.A.N. development stack is ready."
  log "API:      ${API_BASE_URL}"
  log "API docs: ${API_BASE_URL}/docs"
  log "VLM:      ${VLM_BASE_URL}"
  log "Frontend: ${FRONTEND_BASE_URL}"
  log "Logs:     ${LOG_DIR}"
  log "Press Ctrl+C to stop services started by this command."
  printf '\n'

  set +e
  wait -n "${api_pid}" "${vlm_pid}" "${frontend_pid}"
  local service_exit_code=$?
  set -e

  if [[ -f "${STOP_REQUEST_FILE}" ]]; then
    log "Dev stack shutdown was requested."
    return 0
  fi

  log "A managed service exited unexpectedly with code ${service_exit_code}."
  return 1
}


action_down() {
  mkdir -p "${PID_DIR}" "${LOG_DIR}"
  touch "${STOP_REQUEST_FILE}"

  stop_process_group "${FRONTEND_PID_FILE}" "Frontend"
  stop_process_group "${API_PID_FILE}" "API"
  stop_process_group "${VLM_PID_FILE}" "VLM"

  if db_is_running; then
    log "Stopping Postgres..."
    compose stop db
  else
    log "Postgres is already stopped."
  fi

  log "Dev stack is down."
}


print_process_status() {
  local service_name="$1"
  local pid_file="$2"

  local pid
  pid="$(read_pid_file "${pid_file}" 2>/dev/null || true)"

  if [[ -n "${pid}" ]] && pid_is_running "${pid}"; then
    printf '%-10s running (PID %s)\n' "${service_name}:" "${pid}"
  else
    printf '%-10s stopped\n' "${service_name}:"
  fi
}


action_status() {
  mkdir -p "${PID_DIR}" "${LOG_DIR}"

  print_process_status "API" "${API_PID_FILE}"
  print_process_status "VLM" "${VLM_PID_FILE}"
  print_process_status "Frontend" "${FRONTEND_PID_FILE}"

  if db_is_running; then
    printf '%-10s running\n' "Postgres:"
  else
    printf '%-10s stopped\n' "Postgres:"
  fi

  if curl -fsS "${API_BASE_URL}/health" >/dev/null 2>&1; then
    printf '%-10s ready\n' "API HTTP:"
  else
    printf '%-10s unavailable\n' "API HTTP:"
  fi

  if curl -fsS "${FRONTEND_BASE_URL}" >/dev/null 2>&1; then
    printf '%-10s ready\n' "Frontend HTTP:"
  else
    printf '%-10s unavailable\n' "Frontend HTTP:"
  fi

  if curl -fsS \
    -H "Authorization: Bearer ${VLM_API_KEY}" \
    "${VLM_BASE_URL}/models" >/dev/null 2>&1; then
    printf '%-10s ready\n' "VLM HTTP:"
  else
    printf '%-10s unavailable\n' "VLM HTTP:"
  fi
}


case "${1:-up}" in
  up)
    action_up
    ;;
  down)
    action_down
    ;;
  status)
    action_status
    ;;
  *)
    echo "Usage: $0 {up|down|status}" >&2
    exit 2
    ;;
esac
