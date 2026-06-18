#!/usr/bin/env bash
set -euo pipefail

SURYA_VENV="${SURYA_VENV:-$HOME/.venvs/fan-surya}"

python3 -m venv "${SURYA_VENV}"
source "${SURYA_VENV}/bin/activate"

python -m pip install -U pip
pip install surya-ocr

python - <<'PY'
import sys

print("Python:", sys.version)

try:
    import surya
    print("Surya import: ok")
except Exception as error:
    raise SystemExit(f"Surya import failed: {error}") from error
PY

echo "Surya venv ready: ${SURYA_VENV}"
