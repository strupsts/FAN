#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/ml_runtime_env.sh"

SURYA_V1_VENV="${SURYA_V1_VENV:-${ML_RUNTIME_DIR}/venvs/fan-surya-v1}"
IMAGE_PATH="${IMAGE_PATH:-data/test_receipt.jpg}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/fan_surya_v1_ocr}"

if [ ! -f "${IMAGE_PATH}" ]; then
  echo "Image not found: ${IMAGE_PATH}"
  exit 1
fi

source "${SURYA_V1_VENV}/bin/activate"

rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

echo "Running Surya v1 OCR probe..."
echo "Image: ${IMAGE_PATH}"
echo "Output dir: ${OUTPUT_DIR}"

START_TS="$(python - <<'PY'
import time
print(time.perf_counter())
PY
)"

surya_ocr "${IMAGE_PATH}" \
  --output_dir "${OUTPUT_DIR}"

END_TS="$(python - <<'PY'
import time
print(time.perf_counter())
PY
)"

echo
python - <<PY
start = float("${START_TS}")
end = float("${END_TS}")
print(f"Duration: {end - start:.2f}s")
PY

echo
echo "Surya v1 output files:"
find "${OUTPUT_DIR}" -maxdepth 4 -type f -print

echo
echo "Extracted text:"
python - <<'PY'
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from typing import Any

output_dir = Path("/tmp/fan_surya_v1_ocr")
results_files = list(output_dir.rglob("results.json"))

if not results_files:
    raise SystemExit(f"results.json not found under {output_dir}")

results_path = results_files[0]
data = json.loads(results_path.read_text())

texts: list[str] = []

def clean_html(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s+", "\n", value)
    return value.strip()

def collect_text(obj: Any) -> None:
    if isinstance(obj, dict):
        for key in ("text", "html"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                text = clean_html(value) if key == "html" else value.strip()
                if text:
                    texts.append(text)

        for value in obj.values():
            collect_text(value)

    elif isinstance(obj, list):
        for item in obj:
            collect_text(item)

collect_text(data)

deduped: list[str] = []
seen: set[str] = set()

for text in texts:
    normalized = text.strip()
    if normalized and normalized not in seen:
        deduped.append(normalized)
        seen.add(normalized)

print("\n".join(deduped))
print()
print(f"Raw Surya v1 results: {results_path}")
PY
