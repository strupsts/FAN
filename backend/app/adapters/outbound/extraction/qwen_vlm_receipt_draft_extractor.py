from __future__ import annotations

import base64
import json
import math
import re
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain import BudgetBucket, Category, Money, ReceiptDraft, ReceiptItem
from app.domain.category import default_bucket_for_category
from app.ports import (
    InvalidReceiptImageError,
    ReceiptDraftExtractorPort,
    ReceiptExtractionError,
    ReceiptExtractionResult,
    ReceiptExtractorResponseError,
    ReceiptExtractorUnavailableError,
)


SYSTEM_PROMPT = """You are a receipt image parser.

Return ONLY valid JSON.
Do not return markdown.
Do not explain.
Do not include reasoning.

Use this exact JSON shape:
{
  "merchant_name": "string or null",
  "purchased_at": "ISO 8601 datetime string or null",
  "subtotal_amount": "decimal string or null",
  "tax_amount": "decimal string or null",
  "total_amount": "decimal string or null",
  "currency": "CAD",
  "items": [
    {
      "name": "string",
      "quantity": "number or null",
      "unit_price_amount": "decimal string or null",
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
- Use CAD as the default currency.
- merchant_name must be the business name, not the city, address, or receipt type.
- total_amount must be the final amount paid, not the subtotal.
- Extract real purchased items or services only.
- Do not include subtotal, tax, total, payment method, card, barcode, survey,
  authorization, reference, or customer-copy lines as items.
- Use the final charged line price for each item after item-level discounts.
- Copy the printed transaction date and time exactly.
- Do not invent a timezone when the receipt does not show one.
- If a category or bucket is uncertain, use unknown.
- confidence must be between 0 and 1.
"""


class QwenVLMReceiptDraftExtractorAdapter(ReceiptDraftExtractorPort):
    extractor_name = "qwen2.5-vl-7b-awq"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 120.0,
        temperature: float = 0.0,
        max_tokens: int = 1200,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")

        if not model.strip():
            raise ValueError("model must not be empty")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens

    def extract_receipt(
        self,
        *,
        image_bytes: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
        image_ref: str | None = None,
    ) -> ReceiptExtractionResult:
        if not image_bytes:
            raise InvalidReceiptImageError("Receipt image is empty")

        try:
            raw_content, response_json = self._request_completion(
                image_bytes=image_bytes,
                original_filename=original_filename,
                content_type=content_type,
            )

            parsed_json = self._extract_json(raw_content)

            draft = self._to_receipt_draft(
                parsed_json=parsed_json,
                image_ref=image_ref,
            )

            model_output: dict[str, Any] = {
                "parsed": parsed_json,
                "raw_content": raw_content,
                "model": response_json.get("model"),
                "usage": response_json.get("usage"),
            }

            return ReceiptExtractionResult(
                draft=draft,
                extractor_name=self.extractor_name,
                model_output=model_output,
            )
        except ReceiptExtractionError:
            raise
        except Exception as error:
            raise ReceiptExtractorResponseError(
                "Failed to convert VLM output into a receipt draft"
            ) from error

    def _request_completion(
        self,
        *,
        image_bytes: bytes,
        original_filename: str | None,
        content_type: str | None,
    ) -> tuple[str, dict[str, Any]]:
        payload = {
            "model": self.model,
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
                                "url": self._to_data_url(
                                    image_bytes=image_bytes,
                                    original_filename=original_filename,
                                    content_type=content_type,
                                ),
                            },
                        },
                    ],
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
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")

            if error.code == 400 and "failed to load image" in error_body.lower():
                raise InvalidReceiptImageError(
                    "VLM could not decode the receipt image"
                ) from error

            if error.code == 429 or 500 <= error.code <= 599:
                raise ReceiptExtractorUnavailableError(
                    f"VLM service returned HTTP {error.code}"
                ) from error

            raise ReceiptExtractorResponseError(
                f"VLM request failed with HTTP {error.code}: {error_body}"
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ReceiptExtractorUnavailableError(
                f"VLM service is unavailable: {error}"
            ) from error

        try:
            response_json = json.loads(body)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"VLM server returned invalid JSON: {body}") from error

        if not isinstance(response_json, dict):
            raise RuntimeError(
                f"Unexpected VLM response type: {type(response_json).__name__}"
            )

        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(
                f"Unexpected VLM response shape: {response_json}"
            ) from error

        if isinstance(content, str):
            return content, response_json

        if isinstance(content, list):
            text_parts = [
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict)
            ]
            combined = "".join(text_parts).strip()

            if combined:
                return combined, response_json

        raise RuntimeError(f"Unexpected VLM message content: {content}")

    def _to_data_url(
        self,
        *,
        image_bytes: bytes,
        original_filename: str | None,
        content_type: str | None,
    ) -> str:
        mime_type = self._detect_image_mime_type(image_bytes)
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _detect_image_mime_type(self, image_bytes: bytes) -> str:
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"

        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"

        if (
            len(image_bytes) >= 12
            and image_bytes[:4] == b"RIFF"
            and image_bytes[8:12] == b"WEBP"
        ):
            return "image/webp"

        raise InvalidReceiptImageError(
            "Unsupported or invalid image. Supported formats: JPEG, PNG, WEBP"
        )

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
                raise RuntimeError(
                    f"VLM did not return a JSON object: {raw_content}"
                )

            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"VLM returned malformed JSON: {raw_content}"
                ) from error

        if not isinstance(parsed, dict):
            raise RuntimeError(f"VLM JSON must be an object: {parsed}")

        return parsed

    def _to_receipt_draft(
        self,
        *,
        parsed_json: dict[str, Any],
        image_ref: str | None,
    ) -> ReceiptDraft:
        currency = str(parsed_json.get("currency") or "CAD").strip().upper()
        items_json = parsed_json.get("items")

        if not isinstance(items_json, list):
            raise RuntimeError(f"VLM items must be a list: {items_json}")

        items = [
            item
            for item_json in items_json
            if (item := self._to_receipt_item(item_json, currency)) is not None
        ]

        if not items:
            raise RuntimeError(
                f"VLM returned no valid receipt items: {parsed_json}"
            )

        return ReceiptDraft(
            merchant_name=self._to_optional_string(
                parsed_json.get("merchant_name")
            ),
            purchased_at=self._to_datetime_or_none(
                parsed_json.get("purchased_at")
            ),
            items=items,
            subtotal=self._to_money_or_none(
                parsed_json.get("subtotal_amount"),
                currency,
            ),
            tax=self._to_money_or_none(
                parsed_json.get("tax_amount"),
                currency,
            ),
            total=self._to_money_or_none(
                parsed_json.get("total_amount"),
                currency,
            ),
            image_ref=image_ref,
            parser_name=self.extractor_name,
        )

    def _to_receipt_item(
        self,
        item_json: Any,
        currency: str,
    ) -> ReceiptItem | None:
        if not isinstance(item_json, dict):
            return None

        name = self._to_optional_string(item_json.get("name"))

        if not name:
            return None

        total_price = self._to_money_or_none(
            item_json.get("total_price_amount"),
            currency,
        )

        if total_price is None:
            return None

        category = self._to_category(item_json.get("category"))
        bucket = self._to_bucket(item_json.get("bucket"), category)

        return ReceiptItem(
            name=name,
            quantity=self._to_positive_float_or_none(
                item_json.get("quantity")
            ),
            unit_price=self._to_money_or_none(
                item_json.get("unit_price_amount"),
                currency,
            ),
            total_price=total_price,
            category=category,
            bucket=bucket,
            confidence=self._to_confidence(item_json.get("confidence")),
        )

    def _to_money_or_none(
        self,
        value: Any,
        currency: str,
    ) -> Money | None:
        if value is None:
            return None

        text = str(value).strip()

        if not text:
            return None

        normalized = re.sub(r"[^\d,.\-]", "", text).replace(",", "")

        try:
            amount = Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None

        if not amount.is_finite():
            return None

        return Money(amount=amount, currency=currency)

    def _to_datetime_or_none(self, value: Any) -> datetime | None:
        text = self._to_optional_string(value)

        if text is None:
            return None

        normalized = text

        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"

        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _to_category(self, value: Any) -> Category:
        normalized = str(value or "unknown").strip().lower()

        try:
            return Category(normalized)
        except ValueError:
            return Category.UNKNOWN

    def _to_bucket(
        self,
        value: Any,
        category: Category,
    ) -> BudgetBucket:
        normalized = str(value or "").strip().lower()

        if not normalized:
            return default_bucket_for_category(category)

        try:
            return BudgetBucket(normalized)
        except ValueError:
            return default_bucket_for_category(category)

    def _to_confidence(self, value: Any) -> float | None:
        if value is None:
            return None

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(confidence):
            return None

        return max(0.0, min(1.0, confidence))

    def _to_positive_float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None

        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        if not math.isfinite(number) or number <= 0:
            return None

        return number

    def _to_optional_string(self, value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None
