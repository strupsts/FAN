#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/ml_runtime_env.sh"

MINICPM_VLLM_VENV="${MINICPM_VLLM_VENV:-${ML_RUNTIME_DIR}/venvs/fan-vllm-minicpmv45}"
MINICPM_VLLM_VERSION="${MINICPM_VLLM_VERSION:-0.23.0}"

echo "Creating MiniCPM vLLM environment..."
echo "Venv: ${MINICPM_VLLM_VENV}"
echo "vLLM version: ${MINICPM_VLLM_VERSION}"

python3 -m venv "${MINICPM_VLLM_VENV}"
source "${MINICPM_VLLM_VENV}/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install "vllm==${MINICPM_VLLM_VERSION}"

python - <<'PY'
import torch
import transformers
import vllm

print("vLLM:", vllm.__version__)
print("Transformers:", transformers.__version__)
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("PyTorch CUDA:", torch.version.cuda)
PY

echo "MiniCPM vLLM environment ready."
