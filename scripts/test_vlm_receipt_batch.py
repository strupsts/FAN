from __future__ import annotations

import base64
import json
import mimetypes
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


INPUT_DIR = Path(__import__("os").environ.get("INPUT_DIR", "data/receipt_samples"))
IMAGE_PATH_ENV = __import__("os").environ.get("IMAGE_PATH")
OUTPUT_ROOT = Path(__import__("os").environ.get("OUTPUT_ROOT", "/tmp/fan_vlm_qwen25vl7b_awq"))
BASE_URL = __import__("os").environ.get("VLM_BASE_URL", "http://127.0.0.1:8002/v1")
API_KEY = __import__("os").environ.get("VLM_API_KEY", "local-dev-key")
MODEL = __import__("os").environ.get("VLM_MODEL", "local-vlm-receipt-parser")
TIMEOUT_SECONDS = int(__import__("os").environ.get("VLM_TIMEOUT_SECONDS", "300"))
START_COMMAND = __import__("os").environ.get(
    "VLM_START_COMMAND",
    "make vlm-qwen25vl7b-serve",
)
SERVER_CHECK_TIMEOUT_SECONDS = int(__import__("os").environ.get("VLM_SERVER_CHECK_TIMEOUT_SECONDS", "3"))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


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


def find_images() -> list[Path]:
    if IMAGE_PATH_ENV:
        image_path = Path(IMAGE_PATH_ENV)
        if not image_path.exists():
            raise SystemExit(f"IMAGE_PATH not found: {image_path}")
        return [image_path]

    if not INPUT_DIR.exists():
        raise SystemExit(f"INPUT_DIR not found: {INPUT_DIR}")

    images = [
        path
        for path in sorted(INPUT_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    if not images:
        raise SystemExit(
            f"No images found in {INPUT_DIR}. "
            f"Supported extensions: {', '.join(sorted(IMAGE_EXTENSIONS))}"
        )

    return images



def check_vlm_server() -> None:
    url = f"{BASE_URL}/models"

    request = urllib.request.Request(
        url=url,
        headers={
            "Authorization": f"Bearer {API_KEY}",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=SERVER_CHECK_TIMEOUT_SECONDS) as response:
            response.read()
    except urllib.error.URLError as error:
        raise SystemExit(
            "VLM server is not available.\n"
            f"Tried: {url}\n"
            f"Error: {error}\n\n"
            "Start it first in another terminal:\n"
            f"{START_COMMAND}"
        ) from error


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


def build_payload(image_path: Path) -> dict[str, Any]:
    return {
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
                            "url": image_to_data_url(image_path),
                        },
                    },
                ],
            },
        ],
        "temperature": 0,
        "max_tokens": 900,
    }


def request_vlm(image_path: Path) -> tuple[float, dict[str, Any], str]:
    payload = build_payload(image_path)

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
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as error:
        raise RuntimeError(f"VLM request failed for {image_path}: {error}") from error

    finished_at = time.perf_counter()
    response_json = json.loads(body)

    try:
        raw_content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"Unexpected VLM response shape: {response_json}") from error

    return finished_at - started_at, response_json, raw_content


def safe_name(path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", path.stem)


def process_image(image_path: Path, run_dir: Path) -> dict[str, Any]:
    image_output_dir = run_dir / safe_name(image_path)
    image_output_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "image_path": str(image_path),
        "ok": False,
        "request_seconds": None,
        "merchant_name": None,
        "total_amount": None,
        "currency": None,
        "item_count": None,
        "error": None,
        "output_dir": str(image_output_dir),
    }

    print("=" * 80)
    print(f"Image: {image_path}")

    try:
        request_seconds, response_json, raw_content = request_vlm(image_path)
        parsed = extract_json(raw_content)

        (image_output_dir / "response.json").write_text(
            json.dumps(response_json, indent=2, ensure_ascii=False)
        )
        (image_output_dir / "raw_content.txt").write_text(raw_content)
        (image_output_dir / "parsed.json").write_text(
            json.dumps(parsed, indent=2, ensure_ascii=False)
        )

        items = parsed.get("items") or []

        result.update(
            {
                "ok": True,
                "request_seconds": round(request_seconds, 3),
                "merchant_name": parsed.get("merchant_name"),
                "total_amount": parsed.get("total_amount"),
                "currency": parsed.get("currency"),
                "item_count": len(items) if isinstance(items, list) else None,
            }
        )

        print(f"Request seconds: {request_seconds:.2f}")
        print(f"Merchant: {result['merchant_name']}")
        print(f"Total: {result['total_amount']} {result['currency']}")
        print(f"Items: {result['item_count']}")
        print("Parsed JSON:")
        print(json.dumps(parsed, indent=2, ensure_ascii=False))

    except Exception as error:
        result["error"] = str(error)
        print(f"FAILED: {error}")

    print(f"Output dir: {image_output_dir}")
    return result


def main() -> None:
    images = find_images()
    check_vlm_server()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_ROOT / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    summary_path = run_dir / "summary.jsonl"

    print(f"Input dir: {INPUT_DIR}")
    print(f"Images: {len(images)}")
    print(f"Output run dir: {run_dir}")
    print(f"Base URL: {BASE_URL}")
    print(f"Model: {MODEL}")
    print()

    results = []

    for image_path in images:
        result = process_image(image_path=image_path, run_dir=run_dir)
        results.append(result)

        with summary_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(result, ensure_ascii=False) + "\n")

    ok_count = sum(1 for result in results if result["ok"])
    failed_count = len(results) - ok_count

    print("=" * 80)
    print("Batch summary:")
    print(f"OK: {ok_count}")
    print(f"Failed: {failed_count}")
    print(f"Summary: {summary_path}")


if __name__ == "__main__":
    main()
