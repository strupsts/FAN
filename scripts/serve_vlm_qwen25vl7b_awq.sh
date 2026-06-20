#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/ml_runtime_env.sh"

VLM_VENV="${VLM_VENV:-$HOME/.venvs/fan-vllm}"
VLM_MODEL="${VLM_MODEL:-Qwen/Qwen2.5-VL-7B-Instruct-AWQ}"
VLM_SERVED_MODEL_NAME="${VLM_SERVED_MODEL_NAME:-local-vlm-receipt-parser}"
VLM_HOST="${VLM_HOST:-127.0.0.1}"
VLM_PORT="${VLM_PORT:-8002}"
VLM_API_KEY="${VLM_API_KEY:-local-dev-key}"
VLM_MAX_MODEL_LEN="${VLM_MAX_MODEL_LEN:-4096}"
VLM_GPU_MEMORY_UTILIZATION="${VLM_GPU_MEMORY_UTILIZATION:-0.85}"

source "${VLM_VENV}/bin/activate"

echo "Starting VLM vLLM server..."
echo "Model: ${VLM_MODEL}"
echo "Served name: ${VLM_SERVED_MODEL_NAME}"
echo "URL: http://${VLM_HOST}:${VLM_PORT}/v1"
echo "Max model len: ${VLM_MAX_MODEL_LEN}"
echo "GPU memory utilization: ${VLM_GPU_MEMORY_UTILIZATION}"

vllm serve "${VLM_MODEL}" \
  --served-model-name "${VLM_SERVED_MODEL_NAME}" \
  --host "${VLM_HOST}" \
  --port "${VLM_PORT}" \
  --api-key "${VLM_API_KEY}" \
  --max-model-len "${VLM_MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${VLM_GPU_MEMORY_UTILIZATION}" \
  --max-num-seqs 1 \
  --generation-config vllm
