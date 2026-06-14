#!/usr/bin/env bash
set -euo pipefail

VLLM_VENV="${VLLM_VENV:-$HOME/.venvs/fan-vllm}"
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen3-8B-AWQ}"
VLLM_SERVED_MODEL_NAME="${VLLM_SERVED_MODEL_NAME:-local-receipt-parser}"
VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8001}"
VLLM_API_KEY="${VLLM_API_KEY:-local-dev-key}"
VLLM_MAX_MODEL_LEN="${VLLM_MAX_MODEL_LEN:-2048}"
VLLM_GPU_MEMORY_UTILIZATION="${VLLM_GPU_MEMORY_UTILIZATION:-0.85}"

CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-13.1}"
export CUDA_HOME
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"

source "${VLLM_VENV}/bin/activate"

echo "Starting vLLM..."
echo "Model: ${VLLM_MODEL}"
echo "Served name: ${VLLM_SERVED_MODEL_NAME}"
echo "URL: http://${VLLM_HOST}:${VLLM_PORT}/v1"
echo "CUDA_HOME: ${CUDA_HOME}"
echo "NVCC: $(command -v nvcc || echo 'not found')"
echo "Max model len: ${VLLM_MAX_MODEL_LEN}"
echo "GPU memory utilization: ${VLLM_GPU_MEMORY_UTILIZATION}"

nvcc --version

vllm serve "${VLLM_MODEL}" \
  --served-model-name "${VLLM_SERVED_MODEL_NAME}" \
  --host "${VLLM_HOST}" \
  --port "${VLLM_PORT}" \
  --api-key "${VLLM_API_KEY}" \
  --max-model-len "${VLLM_MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${VLLM_GPU_MEMORY_UTILIZATION}" \
  --generation-config vllm
