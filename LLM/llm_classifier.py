

from __future__ import annotations

from typing import Optional

from LLM.schemas_llm import LLMItemRequest, LLMItemResponse

from .llm_core import LLMCore
import json
from typing import Literal

_llm_core = LLMCore()

class LLMClassifier:
    """
    Обёртка вокруг LLMCore, заточенная под задачу:
    "из merchant + item_name_raw + price + lang получить category/bucket/conf/norm_name"
    """

    def __init__(self, core: LLMCore | None = None) -> None:
        # Если core не передали — берём глобальный
        self.core = core or _llm_core

    def classify_item(self, req: LLMItemRequest) -> LLMItemResponse:
        """
        Вызывает Qwen3, чтобы получить JSON с категорией/бакетом/уверенностью.
        Если что-то идёт не так — возвращает UNKNOWN с низким confidence.
        """
        # 1) system-промпт: кто ты и что делаешь
        system_prompt = (
            "You are a strict JSON-only classifier for personal finance purchases.\n"
            "You must ALWAYS answer with a single JSON object and nothing else.\n"
            "Target fields:\n"
            "  - category: one of [DAIRY, MEAT, VEGETABLES, FASTFOOD, COFFEE, "
            "PHARMACY, AUTO, BAKERY, ELECTRONICS, HOUSEHOLD, TAKEOUT, WANTS_OTHER]\n"
            "  - bucket: one of [NEEDS, WANTS]\n"
            "  - confidence: float from 0.0 to 1.0 (model confidence)\n"
            "  - norm_name: short normalized English name for the item\n"
            "If you are not sure, use category='UNKNOWN', bucket='UNKNOWN', confidence<=0.2.\n"
        )

        # 2) user-пейлоад: просто данные в JSON
        user_payload = {
            "merchant": req.merchant,
            "item_name_raw": req.item_name_raw,
            "price": req.price,
            "lang": req.lang,
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "Classify this purchase and return ONLY JSON:\n"
                    + json.dumps(user_payload, ensure_ascii=False)
                ),
            },
        ]

        # 3) выстреливаем в LLM
        try:
            content = self.core.chat(messages, temperature=0.1, max_tokens=800)
        except Exception:
            # LLM вообще не ответила
            return LLMItemResponse(
                category="UNKNOWN",
                bucket="UNKNOWN",
                confidence=0.2,
                norm_name=req.item_name_raw,
            )

        # 4) Пытаемся распарсить JSON
        try:
            data = json.loads(content)
        except Exception:
            # Модель начала философствовать, вернулась невалидная строка
            return LLMItemResponse(
                category="UNKNOWN",
                bucket="UNKNOWN",
                confidence=0.2,
                norm_name=req.item_name_raw,
            )

        # 5) Достаём поля с дефолтами
        category = str(data.get("category", "UNKNOWN")).strip().upper()
        bucket = str(data.get("bucket", "UNKNOWN")).strip().upper()
        confidence = float(data.get("confidence", 0.2))
        norm_name = str(data.get("norm_name", req.item_name_raw))

        # Немного страхуем:
        if confidence < 0.0:
            confidence = 0.0
        if confidence > 1.0:
            confidence = 1.0

        # 6) Возвращаем pydantic-модель
        return LLMItemResponse(
            category=category,
            bucket=bucket,
            confidence=confidence,
            norm_name=norm_name,
        )
