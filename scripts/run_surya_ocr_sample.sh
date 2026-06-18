#!/usr/bin/env bash
set -euo pipefail

SURYA_VENV="${SURYA_VENV:-$HOME/.venvs/fan-surya}"
IMAGE_PATH="${IMAGE_PATH:-data/test_receipt.jpg}"
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/fan_surya_ocr}"

if [ ! -f "${IMAGE_PATH}" ]; then
  echo "Image not found: ${IMAGE_PATH}"
  exit 1
fi

source "${SURYA_VENV}/bin/activate"

rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

echo "Running Surya OCR..."
echo "Image: ${IMAGE_PATH}"
echo "Output dir: ${OUTPUT_DIR}"

surya_ocr "${IMAGE_PATH}" \
  --output_dir "${OUTPUT_DIR}"

echo
echo "Surya output files:"
find "${OUTPUT_DIR}" -maxdepth 3 -type f -print

echo
echo "Extracted text:"
python - <<'PY'
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

output_dir = Path("/tmp/fan_surya_ocr")
results_files = list(output_dir.rglob("results.json"))

if not results_files:
    raise SystemExit(f"results.json not found under {output_dir}")

results_path = results_files[0]
data = json.loads(results_path.read_text())

texts: list[str] = []

def html_to_text(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s+", "\n", value)
    return value.strip()

for pages in data.values():
    for page in pages:
        blocks = page.get("blocks", [])
        blocks = sorted(blocks, key=lambda block: block.get("reading_order", 0))

        for block in blocks:
            if block.get("skipped") or block.get("error"):
                continue

            html = block.get("html") or ""
            text = html_to_text(html)
            if text:
                texts.append(text)

print("\n".join(texts))
print()
print(f"Raw Surya results: {results_path}")
PY
