#!/usr/bin/env bash
set -euo pipefail

# === базовые пути ===
FAN_DIR="$HOME/FAN"
VLLM_DIR="$HOME/vllm-qwen"

RUN_DIR="$FAN_DIR/.run"
LOG_DIR="$FAN_DIR/logs"
VLLM_PORT=8000

mkdir -p "$RUN_DIR" "$LOG_DIR"

# === helpers ===

activate_venv() {
  local dir="$1"
  if [[ -f "$dir/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1090
    source "$dir/.venv/bin/activate"
  else
    echo "WARN: no venv in $dir (.venv/bin/activate not found)" >&2
  fi
}

is_pid_running() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
  fi
  return 1
}

status_line() {
  local name="$1"
  local ok="$2"
  if [[ "$ok" == "1" ]]; then
    printf "%-12s | \e[32mRUNNING\e[0m\n" "$name"
  else
    printf "%-12s | \e[31mSTOPPED\e[0m\n" "$name"
  fi
}

status_all() {
  local redis_ok=0
  local vllm_ok=0

  if systemctl is-active --quiet redis-server; then
    redis_ok=1
  fi

  if is_pid_running "$RUN_DIR/vllm.pid"; then
    vllm_ok=1
  fi

  echo "=== STATUS ==="
  status_line "redis" "$redis_ok"
  status_line "vLLM"  "$vllm_ok"
  echo
}

# === redis ===

start_redis() {
  sudo systemctl start redis-server
}

stop_redis() {
  sudo systemctl stop redis-server || true
}

# === vLLM ===

start_vllm() {
  local pidf="$RUN_DIR/vllm.pid"

  if is_pid_running "$pidf"; then
    echo "vLLM already running (pid $(cat "$pidf"))"
    return 0
  fi

  (
    cd "$VLLM_DIR"
    activate_venv "$VLLM_DIR"
    nohup vllm serve Qwen/Qwen3-8B-AWQ \
      --served-model-name qwen3-8b \
      --host 0.0.0.0 --port "$VLLM_PORT" \
      --max-model-len 2048 \
      --gpu-memory-utilization 0.85 \
      > "$LOG_DIR/vllm.log" 2>&1 &
    echo $! > "$pidf"
  )

  echo "vLLM starting... log: $LOG_DIR/vllm.log"
}

stop_vllm() {
  local pidf="$RUN_DIR/vllm.pid"

  if is_pid_running "$pidf"; then
    kill "$(cat "$pidf")" 2>/dev/null || true
    rm -f "$pidf"
  else
    # fallback, если pid-файл потеряли
    pkill -f "vllm serve Qwen/Qwen3-8B-AWQ" 2>/dev/null || true
    rm -f "$pidf" 2>/dev/null || true
  fi
}

# === общие операции ===

start_all() {
  start_redis
  start_vllm
}

stop_all() {
  stop_vllm
  stop_redis
}

restart_all() {
  stop_all
  start_all
}

# === CLI ===

case "${1:-menu}" in
  status)
    status_all
    ;;
  start)
    start_all
    ;;
  stop)
    stop_all
    ;;
  restart)
    restart_all
    ;;
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
        1) start_all ;;
        2) stop_all ;;
        3) restart_all ;;
        4) status_all ;;
        0) exit 0 ;;
      esac
      echo
    done
    ;;
esac
