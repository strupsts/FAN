#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/ml_runtime_env.sh"

SURYA_V1_VENV="${SURYA_V1_VENV:-${ML_RUNTIME_DIR}/venvs/fan-surya-v1}"
SURYA_V1_VERSION="${SURYA_V1_VERSION:-0.16.7}"

python3 -m venv "${SURYA_V1_VENV}"
source "${SURYA_V1_VENV}/bin/activate"

python -m pip install -U pip

echo "Installing surya-ocr==${SURYA_V1_VERSION}"
pip install \
  "surya-ocr==${SURYA_V1_VERSION}" \
  requests \
  "transformers==4.57.3" \
  "huggingface-hub<1" \
  "tokenizers<0.23,>=0.22"

python - <<'PY'
import sys

print("Python:", sys.version)

try:
    import surya
    print("Surya v1 import: ok")
    print("Surya module:", surya)
except Exception as error:
    raise SystemExit(f"Surya v1 import failed: {error}") from error

try:
    import transformers
    import huggingface_hub
    import tokenizers

    print("transformers:", transformers.__version__)
    print("huggingface_hub:", huggingface_hub.__version__)
    print("tokenizers:", tokenizers.__version__)
except Exception as error:
    raise SystemExit(f"Dependency check failed: {error}") from error
PY

echo "Surya v1 venv ready: ${SURYA_V1_VENV}"
