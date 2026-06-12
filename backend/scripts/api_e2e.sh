#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
RECEIPT_IMAGE_PATH="${RECEIPT_IMAGE_PATH:-data/test_receipt.jpg}"

PROCESS_RESPONSE_FILE="/tmp/fan_process_response.json"
CONFIRM_REQUEST_FILE="/tmp/fan_confirm_receipt.json"
CONFIRM_RESPONSE_FILE="/tmp/fan_confirm_response.json"
HISTORY_RESPONSE_FILE="/tmp/fan_history_response.json"
SUMMARY_RESPONSE_FILE="/tmp/fan_summary_response.json"

echo "Checking API health..."
if ! curl -fsS "${API_BASE_URL}/health" > /dev/null; then
  echo "API is not running."
  echo "Start it in another terminal with: make api"
  exit 1
fi

echo "Checking database health..."
if ! curl -fsS "${API_BASE_URL}/health/db" > /dev/null; then
  echo "Database is not available."
  echo "Start Docker/Postgres with: make db-up"
  exit 1
fi

echo "Processing receipt..."
curl -fsS -X POST "${API_BASE_URL}/api/receipts/process" \
  -F "file=@${RECEIPT_IMAGE_PATH}" \
  -o "${PROCESS_RESPONSE_FILE}"

python3 - <<'PY'
import json
from pathlib import Path

process_response = json.loads(Path("/tmp/fan_process_response.json").read_text())

confirm_request = {
    "draft_id": process_response["id"],
    "merchant_name": process_response["merchant_name"],
    "image_ref": process_response["image_ref"],
    "total_amount": process_response["total"]["amount"],
    "total_currency": process_response["total"]["currency"],
    "items": [
        {
            "name": item["name"],
            "total_price_amount": item["total_price"]["amount"],
            "total_price_currency": item["total_price"]["currency"],
            "category": item["category"],
            "bucket": item["bucket"],
            "confidence": item["confidence"],
        }
        for item in process_response["items"]
    ],
}

Path("/tmp/fan_confirm_receipt.json").write_text(
    json.dumps(confirm_request, indent=2),
)
PY

echo "Confirming receipt..."
curl -fsS -X POST "${API_BASE_URL}/api/receipts/confirm" \
  -H "Content-Type: application/json" \
  -d @"${CONFIRM_REQUEST_FILE}" \
  -o "${CONFIRM_RESPONSE_FILE}"

echo "Fetching history..."
curl -fsS "${API_BASE_URL}/api/receipts/history" \
  -o "${HISTORY_RESPONSE_FILE}"

echo "Fetching summary..."
curl -fsS "${API_BASE_URL}/api/receipts/summary?from_date=2026-01-01&to_date=2026-12-31" \
  -o "${SUMMARY_RESPONSE_FILE}"

python3 - <<'PY'
import json
from pathlib import Path

process_response = json.loads(Path("/tmp/fan_process_response.json").read_text())
confirm_response = json.loads(Path("/tmp/fan_confirm_response.json").read_text())
history_response = json.loads(Path("/tmp/fan_history_response.json").read_text())
summary_response = json.loads(Path("/tmp/fan_summary_response.json").read_text())

print()
print("API E2E result:")
print(f"Draft ID: {process_response['id']}")
print(f"Confirmed receipt ID: {confirm_response['id']}")
print(f"History count: {len(history_response)}")
print(f"Summary total: {summary_response['total_spent']['amount']} {summary_response['total_spent']['currency']}")
print(f"Categories: {summary_response['by_category']}")
print(f"Merchants: {summary_response['by_merchant']}")

if len(history_response) < 1:
    raise SystemExit("Expected at least one receipt in history")

if summary_response["total_spent"]["amount"] == "0.00":
    raise SystemExit("Expected summary total to be greater than zero")

print()
print("API E2E passed.")
PY
