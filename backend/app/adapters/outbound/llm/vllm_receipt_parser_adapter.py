from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain import BudgetBucket, Category, Money, ReceiptDraft, ReceiptItem
from app.domain.category import default_bucket_for_category
from app.ports import OCRResult, ReceiptParserPort


SYSTEM_PROMPT = """You are a receipt OCR parser.

Return ONLY valid JSON.
Do not return markdown.
Do not explain.
Do not include reasoning.
Do not include <think> blocks.

Use this exact JSON shape:
{
  "merchant_name": "string or null",
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
- Do not include tax/total lines as items unless they are the only lines available.
- If category is uncertain, use unknown.
- If bucket is uncertain, use the default bucket for the category or unknown.
- confidence must be between 0 and 1.
"""


class VLLMReceiptParserAdapter(ReceiptParserPort):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        temperature: float,
        max_tokens: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens

    def parse_receipt(self, ocr_result: OCRResult, image_ref: str | None = None) -> ReceiptDraft:
        raw_content = self._request_completion(ocr_result.full_text)
        parsed_json = self._extract_json(raw_content)

        return self._to_receipt_draft(
            parsed_json=parsed_json,
            ocr_result=ocr_result,
            image_ref=image_ref,
        )

    def _request_completion(self, ocr_text: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Parse this receipt OCR text into the required JSON shape. /no_think\n\nOCR text:\n{ocr_text}",
                },
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        request = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except urllib.error.URLError as error:
            raise RuntimeError(f"vLLM receipt parser request failed: {error}") from error

        response_json = json.loads(body)

        try:
            return response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected vLLM response shape: {response_json}") from error

    def _extract_json(self, raw_content: str) -> dict[str, Any]:
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
                raise RuntimeError(f"vLLM did not return JSON: {raw_content}")

            parsed = json.loads(match.group(0))

        if not isinstance(parsed, dict):
            raise RuntimeError(f"vLLM JSON must be an object: {parsed}")

        return parsed

    def _to_receipt_draft(
        self,
        parsed_json: dict[str, Any],
        ocr_result: OCRResult,
        image_ref: str | None,
    ) -> ReceiptDraft:
        currency = str(parsed_json.get("currency") or "CAD").upper()
        items_json = parsed_json.get("items") or []

        if not isinstance(items_json, list):
            raise RuntimeError(f"vLLM items must be a list: {items_json}")

        items = [self._to_receipt_item(item_json, currency) for item_json in items_json]
        items = [item for item in items if item is not None]

        if not items:
            raise RuntimeError(f"vLLM returned no valid receipt items: {parsed_json}")

        total_amount = parsed_json.get("total_amount")
        total = self._to_money_or_none(total_amount, currency)

        return ReceiptDraft(
            merchant_name=self._to_optional_string(parsed_json.get("merchant_name")),
            items=items,
            total=total,
            image_ref=image_ref,
            raw_ocr_text=ocr_result.full_text,
            parser_name="vllm_receipt_parser",
        )

    def _to_receipt_item(self, item_json: Any, default_currency: str) -> ReceiptItem | None:
        if not isinstance(item_json, dict):
            return None

        name = self._to_optional_string(item_json.get("name"))
        if not name:
            return None

        total_price = self._to_money_or_none(
            item_json.get("total_price_amount"),
            default_currency,
        )
        if total_price is None:
            return None

        category = self._to_category(item_json.get("category"))
        bucket = self._to_bucket(item_json.get("bucket"), category)
        confidence = self._to_confidence(item_json.get("confidence"))

        return ReceiptItem(
            name=name,
            total_price=total_price,
            category=category,
            bucket=bucket,
            confidence=confidence,
        )

    def _to_money_or_none(self, value: Any, currency: str) -> Money | None:
        if value is None:
            return None

        try:
            amount = Decimal(str(value).replace("$", "").strip())
        except (InvalidOperation, ValueError):
            return None

        return Money(amount=amount, currency=currency)

    def _to_category(self, value: Any) -> Category:
        try:
            return Category(str(value or "unknown").strip())
        except ValueError:
            return Category.UNKNOWN

    def _to_bucket(self, value: Any, category: Category) -> BudgetBucket:
        try:
            return BudgetBucket(str(value or "").strip())
        except ValueError:
            return default_bucket_for_category(category)

    def _to_confidence(self, value: Any) -> float | None:
        if value is None:
            return None

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return None

        return max(0.0, min(1.0, confidence))

    def _to_optional_string(self, value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None
