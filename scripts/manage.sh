#!/usr/bin/env bash
set -euo pipefail

# === Настройки путей (поправим после clone) ===
VLLM_DIR="$HOME/vllm-qwen"
APP_DIR="$HOME/CategoryBrain"   # после clone будет так
VLLM_PORT=8000

# процессы/команды — поправим под твой реальный старт позже
VLLM_CMD="cd \"$VLLM_DIR\" && source .venv/bin/activate && vllm serve Qwen/Qwen3-8B-AWQ --served-model-name qwen3-8b --host 0.0.0.0 --port $VLLM_PORT --max-model-len 2048 --gpu-memory-utilization 0.85"

# ===== helpers =====
is_listen() { ss -ltn | grep -q ":$1 "; }

status_line() {
  local name="$1"; local ok="$2"
  if [[ "$ok" == "1" ]]; then
    printf "%-12s | \e[32mRUNNING\e[0m\n" "$name"
  else
    printf "%-12s | \e[31mSTOPPED\e[0m\n" "$name"
  fi
}

status_all() {
  local redis_ok=0 vllm_ok=0
  systemctl is-active --quiet redis-server && redis_ok=1 || true
  is_listen "$VLLM_PORT" && vllm_ok=1 || true

  echo "=== STATUS ==="
  status_line "redis" "$redis_ok"
  status_line "vLLM"  "$vllm_ok"
  echo
}

start_redis() {
  sudo systemctl start redis-server
}

start_vllm() {
  # если уже слушает порт — не стартуем второй раз
  if is_listen "$VLLM_PORT"; then
    echo "vLLM already running on port $VLLM_PORT"
    return 0
  fi

  # запускаем в фоне через nohup
  nohup bash -lc "$VLLM_CMD" > "$HOME/vllm.log" 2>&1 &
  echo "vLLM starting... log: $HOME/vllm.log"
}

stop_vllm() {
  # грубо, но работает: гасим процесс vllm serve
  pkill -f "vllm serve" || true
}

case "${1:-menu}" in
  status) status_all ;;
  start)
    start_redis
    start_vllm
    ;;
  stop)
    stop_vllm
    sudo systemctl stop redis-server
    ;;
  restart)
    stop_vllm
    sudo systemctl restart redis-server
    start_vllm
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
