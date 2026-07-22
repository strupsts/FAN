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
    "purchased_at": process_response["purchased_at"],
    "image_ref": process_response["image_ref"],
    "subtotal_amount": (
        process_response["subtotal"]["amount"]
        if process_response["subtotal"] is not None
        else None
    ),
    "subtotal_currency": (
        process_response["subtotal"]["currency"]
        if process_response["subtotal"] is not None
        else process_response["total"]["currency"]
    ),
    "tax_amount": (
        process_response["tax"]["amount"]
        if process_response["tax"] is not None
        else None
    ),
    "tax_currency": (
        process_response["tax"]["currency"]
        if process_response["tax"] is not None
        else process_response["total"]["currency"]
    ),
    "total_amount": process_response["total"]["amount"],
    "total_currency": process_response["total"]["currency"],
    "items": [
        {
            "name": item["name"],
            "total_price_amount": item["total_price"]["amount"],
            "total_price_currency": item["total_price"]["currency"],
            "category": item["category"],
            "bucket": item["bucket"],
            "quantity": item["quantity"],
            "unit_price_amount": (
                item["unit_price"]["amount"]
                if item["unit_price"] is not None
                else None
            ),
            "unit_price_currency": (
                item["unit_price"]["currency"]
                if item["unit_price"] is not None
                else item["total_price"]["currency"]
            ),
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

PURCHASE_DATE="$(
  python3 - <<'PY_INNER'
import json
from pathlib import Path

response = json.loads(
    Path("/tmp/fan_process_response.json").read_text()
)

purchased_at = response.get("purchased_at")

if not purchased_at:
    raise SystemExit("Process response has no purchased_at")

print(purchased_at[:10])
PY_INNER
)"

curl -fsS \
  "${API_BASE_URL}/api/receipts/summary?from_date=${PURCHASE_DATE}&to_date=${PURCHASE_DATE}" \
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

confirmed_history_receipt = next(
    (
        receipt
        for receipt in history_response
        if receipt["id"] == confirm_response["id"]
    ),
    None,
)

if confirmed_history_receipt is None:
    raise SystemExit(
        "Confirmed receipt was not found in history"
    )

for field_name in (
    "merchant_name",
    "purchased_at",
    "subtotal",
    "tax",
    "total",
):
    if confirmed_history_receipt[field_name] != confirm_response[field_name]:
        raise SystemExit(
            f"History round-trip mismatch for {field_name}"
        )

if confirmed_history_receipt["items"] != confirm_response["items"]:
    raise SystemExit("History item round-trip mismatch")

print()
print("API E2E passed.")
PY
