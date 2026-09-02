#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/ml_runtime_env.sh"
source "${REPO_ROOT}/ml-runtime/model.env"

VLM_HOST="${VLM_HOST:-127.0.0.1}"
VLM_PORT="${VLM_PORT:-8002}"
VLM_API_KEY="${VLM_API_KEY:-local-dev-key}"
VLM_MAX_MODEL_LEN="${VLM_MAX_MODEL_LEN:-4096}"
VLM_GPU_MEMORY_UTILIZATION="${VLM_GPU_MEMORY_UTILIZATION:-0.85}"

if [[ ! -x "${VLM_VENV}/bin/vllm" ]]; then
  echo "VLM runtime is not provisioned at ${VLM_VENV}." >&2
  echo "Run: make provision" >&2
  exit 1
fi

mkdir -p "${HF_HOME}" "${XDG_CACHE_HOME}" "${TORCH_HOME}" "${PIP_CACHE_DIR}"

source "${VLM_VENV}/bin/activate"

echo "Starting VLM vLLM server..."
echo "Model: ${VLM_MODEL}"
echo "Revision: ${VLM_MODEL_REVISION}"
echo "Served name: ${VLM_SERVED_MODEL_NAME}"
echo "URL: http://${VLM_HOST}:${VLM_PORT}/v1"
echo "Max model len: ${VLM_MAX_MODEL_LEN}"
echo "GPU memory utilization: ${VLM_GPU_MEMORY_UTILIZATION}"

vllm serve "${VLM_MODEL}" \
  --revision "${VLM_MODEL_REVISION}" \
  --served-model-name "${VLM_SERVED_MODEL_NAME}" \
  --host "${VLM_HOST}" \
  --port "${VLM_PORT}" \
  --api-key "${VLM_API_KEY}" \
  --max-model-len "${VLM_MAX_MODEL_LEN}" \
  --gpu-memory-utilization "${VLM_GPU_MEMORY_UTILIZATION}" \
  --limit-mm-per-prompt '{"image": 1, "video": 0}' \
  --max-num-seqs 1 \
  --generation-config vllm
