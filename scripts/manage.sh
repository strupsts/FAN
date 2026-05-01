#!/usr/bin/env bash
set -euo pipefail

# === базовые пути ===
APP_DIR="$HOME/FAN"
VLLM_DIR="$HOME/vllm-qwen"

RUN_DIR="$APP_DIR/.run"
LOG_DIR="$APP_DIR/logs"

VLLM_PORT=8000   # vLLM
API_PORT=8010    # FastAPI

mkdir -p "$RUN_DIR" "$LOG_DIR"

REDIS_PID_FILE="$RUN_DIR/redis.pid"
VLLM_PID_FILE="$RUN_DIR/vllm.pid"
API_PID_FILE="$RUN_DIR/api.pid"
WORKER_PID_FILE="$RUN_DIR/worker.pid"

# === helpers ===
activate_venv() {
  local dir="$1"
  if [[ -f "$dir/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$dir/.venv/bin/activate"
  else
    echo "No .venv in $dir" >&2
    return 1
  fi
}

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

status_line() {
  local name="$1"; local ok="$2"
  if [[ "$ok" == "1" ]]; then
    printf "%-12s | \e[32mRUNNING\e[0m\n" "$name"
  else
    printf "%-12s | \e[31mSTOPPED\e[0m\n" "$name"
  fi
}

status_all() {
  local redis_ok=0 vllm_ok=0 api_ok=0 worker_ok=0

  # redis
  if command -v systemctl >/dev/null 2>&1; then
    systemctl is-active --quiet redis-server && redis_ok=1 || true
  else
    pgrep -x redis-server >/dev/null 2>&1 && redis_ok=1 || true
  fi

  # vLLM: по PID
  if [[ -f "$VLLM_PID_FILE" ]] && is_pid_running "$(cat "$VLLM_PID_FILE")"; then
    vllm_ok=1
  fi

  # API: по PID
  if [[ -f "$API_PID_FILE" ]] && is_pid_running "$(cat "$API_PID_FILE")"; then
    api_ok=1
  fi

  # worker: по PID
  if [[ -f "$WORKER_PID_FILE" ]] && is_pid_running "$(cat "$WORKER_PID_FILE")"; then
    worker_ok=1
  fi

  echo "=== STATUS ==="
  status_line "redis"      "$redis_ok"
  status_line "vLLM"       "$vllm_ok"
  status_line "api"        "$api_ok"
  status_line "rq-worker"  "$worker_ok"
  echo
}

# === redis ===
start_redis() {
  echo "Starting redis..."
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl start redis-server
  else
    sudo service redis-server start
  fi
}

stop_redis() {
  echo "Stopping redis..."
  if command -v systemctl >/dev/null 2>&1; then
    sudo systemctl stop redis-server || true
  else
    sudo service redis-server stop || true
  fi
}

# === vLLM ===
start_vllm() {
  local pidf="$VLLM_PID_FILE"

  if [[ -f "$pidf" ]] && is_pid_running "$(cat "$pidf")"; then
    echo "vLLM already running (PID $(cat "$pidf"))"
    return 0
  fi

  echo "Starting vLLM on :$VLLM_PORT..."
  (
    cd "$VLLM_DIR"
    activate_venv "$VLLM_DIR"
    nohup vllm serve Qwen/Qwen3-8B-AWQ \
      --served-model-name qwen3-8b \
      --host 0.0.0.0 \
      --port "$VLLM_PORT" \
      --max-model-len 2048 \
      --gpu-memory-utilization 0.85 \
      > "$LOG_DIR/vllm.log" 2>&1 &
    echo $! > "$pidf"
  )
  echo "vLLM starting... log: $LOG_DIR/vllm.log"
}

stop_vllm() {
  local pidf="$VLLM_PID_FILE"

  if [[ -f "$pidf" ]]; then
    local pid
    pid="$(cat "$pidf")"
    if is_pid_running "$pid"; then
      echo "Stopping vLLM (PID $pid)..."
      kill "$pid" || true
    fi
    rm -f "$pidf"
  else
    pkill -f "vllm serve" || true
  fi
}

# === FastAPI API ===
start_api() {
  local pidf="$API_PID_FILE"

  if [[ -f "$pidf" ]] && is_pid_running "$(cat "$pidf")"; then
    echo "API already running (PID $(cat "$pidf"))"
    return 0
  fi

  echo "Starting FastAPI on :$API_PORT..."
  (
    cd "$APP_DIR"
    activate_venv "$APP_DIR"
    nohup python -m API.api > "$LOG_DIR/api.log" 2>&1 &
    echo $! > "$pidf"
  )
  echo "API starting... log: $LOG_DIR/api.log"
}

stop_api() {
  local pidf="$API_PID_FILE"

  if [[ -f "$pidf" ]]; then
    local pid
    pid="$(cat "$pidf")"
    if is_pid_running "$pid"; then
      echo "Stopping API (PID $pid)..."
      kill "$pid" || true
    fi
    rm -f "$pidf"
  else
    pkill -f "python -m API.api" || true
  fi
}

# === RQ worker ===
start_worker() {
  local pidf="$WORKER_PID_FILE"

  if [[ -f "$pidf" ]] && is_pid_running "$(cat "$pidf")"; then
    echo "Worker already running (PID $(cat "$pidf"))"
    return 0
  fi

  echo "Starting RQ worker..."
  (
    cd "$APP_DIR"
    activate_venv "$APP_DIR"
    nohup python -m API.redis.worker > "$LOG_DIR/worker.log" 2>&1 &
    echo $! > "$pidf"
  )
  echo "Worker starting... log: $LOG_DIR/worker.log"
}

stop_worker() {
  local pidf="$WORKER_PID_FILE"

  if [[ -f "$pidf" ]]; then
    local pid
    pid="$(cat "$pidf")"
    if is_pid_running "$pid"; then
      echo "Stopping worker (PID $pid)..."
      kill "$pid" || true
    fi
    rm -f "$pidf"
  else
    pkill -f "python -m API.redis.worker" || true
  fi
}

# === high-level ===
start_all() {
  start_redis
  start_vllm
  start_api
  start_worker
}

stop_all() {
  stop_worker
  stop_api
  stop_vllm
  stop_redis
}

restart_all() {
  stop_all
  start_all
}

case "${1:-menu}" in
  status)   status_all ;;
  start)    start_all ;;
  stop)     stop_all ;;
  restart)  restart_all ;;
  menu|*)
    while true; do
      status_all
      echo "1) start all"
      echo "2) stop all"
      echo "3) restart all"
      echo "4) status"
      echo "0) exit"
      read -r -p "> " choice
      case "$choice" in
        1) "$0" start ;;
        2) "$0" stop ;;
        3) "$0" restart ;;
        4) "$0" status ;;
        0) exit 0 ;;
      esac
      echo
    done
    ;;
esac
