from __future__ import annotations

import base64
import json
import mimetypes
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


IMAGE_PATH = Path("data/test_receipt.jpg")
OUTPUT_DIR = Path("/tmp/fan_vlm_qwen25vl7b_awq")
BASE_URL = "http://127.0.0.1:8002/v1"
API_KEY = "local-dev-key"
MODEL = "local-vlm-receipt-parser"


SYSTEM_PROMPT = """You are a receipt image parser.

Return ONLY valid JSON.
Do not return markdown.
Do not explain.
Do not include reasoning.

Use this exact JSON shape:
{
  "merchant_name": "string or null",
  "purchased_at": "ISO datetime string or null",
  "total_amount": "decimal string or null",
  "currency": "CAD",
  "items": [
    {
      "name": "string",
      "total_price_amount": "decimal string",
      "category": "one of allowed categories",
      "bucket": "one of allowed buckets",
      "confidence": 0.0
    }
  ]
}

Allowed categories:
groceries, restaurants, transport, auto, household, health, personal_care,
entertainment, clothing, electronics, tools, fees, tax, discount, other, unknown

Allowed buckets:
needs, wants, savings, debt, unknown

Rules:
- Use CAD as default currency.
- Extract real purchased items/services only.
- Do not include payment method lines as items.
- Do not include survey, contest, barcode, authorization, card, reference, or customer-copy lines as items.
- If category is uncertain, use unknown.
- confidence must be between 0 and 1.
"""


def image_to_data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def extract_json(raw_content: str) -> dict[str, Any]:
    content = raw_content.strip()

    content = re.sub(
        pattern=r"<think>.*?</think>",
        repl="",
        string=content,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise RuntimeError(f"VLM did not return JSON:\n{raw_content}")

        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise RuntimeError(f"VLM JSON must be an object: {parsed}")

    return parsed


def main() -> None:
    if not IMAGE_PATH.exists():
        raise SystemExit(f"Image not found: {IMAGE_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Parse this receipt image into the required JSON shape.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_data_url(IMAGE_PATH),
                        },
                    },
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 900,
    }

    request = urllib.request.Request(
        url=f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )

    started_at = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as error:
        raise SystemExit(f"VLM request failed: {error}") from error

    finished_at = time.perf_counter()
    request_seconds = finished_at - started_at

    response_json = json.loads(body)
    raw_content = response_json["choices"][0]["message"]["content"]

    raw_response_path = OUTPUT_DIR / "response.json"
    raw_content_path = OUTPUT_DIR / "raw_content.txt"
    parsed_json_path = OUTPUT_DIR / "parsed.json"

    raw_response_path.write_text(json.dumps(response_json, indent=2, ensure_ascii=False))
    raw_content_path.write_text(raw_content)

    print(f"Request seconds: {request_seconds:.2f}")
    print()
    print("Raw content:")
    print(raw_content)
    print()

    try:
        parsed = extract_json(raw_content)
    except Exception as error:
        print(f"JSON parse failed: {error}")
        print(f"Raw response saved to: {raw_response_path}")
        print(f"Raw content saved to: {raw_content_path}")
        raise

    parsed_json_path.write_text(json.dumps(parsed, indent=2, ensure_ascii=False))

    print("Parsed JSON:")
    print(json.dumps(parsed, indent=2, ensure_ascii=False))
    print()
    print(f"Raw response saved to: {raw_response_path}")
    print(f"Raw content saved to: {raw_content_path}")
    print(f"Parsed JSON saved to: {parsed_json_path}")


if __name__ == "__main__":
    main()
