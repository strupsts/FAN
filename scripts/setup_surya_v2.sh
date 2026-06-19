#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/ml_runtime_env.sh"

SURYA_V2_VENV="${SURYA_V2_VENV:-${ML_RUNTIME_DIR}/venvs/fan-surya-v2}"

python3 -m venv "${SURYA_V2_VENV}"
source "${SURYA_V2_VENV}/bin/activate"

python -m pip install -U pip
pip install surya-ocr

python - <<'PY'
import sys

print("Python:", sys.version)

try:
    import surya
    print("Surya v2 import: ok")
    print("Surya module:", surya)
except Exception as error:
    raise SystemExit(f"Surya v2 import failed: {error}") from error
PY

echo "Surya v2 venv ready: ${SURYA_V2_VENV}"
