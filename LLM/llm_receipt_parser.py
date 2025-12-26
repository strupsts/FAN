from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from LLM.schemas_llm import LLMReceiptParseResult
from .llm_core import LLMCore

_llm_core = LLMCore()

# допустимые значения из твоей pydantic-схемы
ALLOWED_CATEGORIES = {
    "DAIRY",
    "MEAT",
    "VEGETABLES",
    "FASTFOOD",
    "COFFEE",
    "PHARMACY",
    "AUTO",
    "BAKERY",
    "ELECTRONICS",
    "HOUSEHOLD",
    "TAKEOUT",
    "WANTS_OTHER",
    "UNKNOWN",
}
ALLOWED_BUCKETS = {"NEEDS", "WANTS", "UNKNOWN"}


def _normalize_category(raw: Any) -> str:
    """
    Превращаем всё, что возвращает модель, в одно из ALLOWED_CATEGORIES.
    Если не вписывается — UNKNOWN.
    Плюс простые синонимы: HEALTHCARE -> PHARMACY и т.п.
    """
    if raw is None:
        return "UNKNOWN"

    s = str(raw).strip().upper()
    if not s:
        return "UNKNOWN"

    # простые хелс-кейсы
    if any(tok in s for tok in ("HEALTH", "PHARM", "MEDIC")):
        return "PHARMACY"

    if s in ALLOWED_CATEGORIES:
        return s

    return "UNKNOWN"


def _normalize_bucket(raw: Any) -> str:
    """
    То же самое для bucket: приводим к NEEDS/WANTS/UNKNOWN.
    """
    if raw is None:
        return "UNKNOWN"

    s = str(raw).strip().upper()
    if not s:
        return "UNKNOWN"

    # медицина/здоровье почти всегда NEEDS
    if any(tok in s for tok in ("MEDIC", "HEALTH", "PHARM")):
        return "NEEDS"

    if s in ALLOWED_BUCKETS:
        return s

    return "UNKNOWN"


def _extract_json_obj(text: str) -> Optional[Dict[str, Any]]:
    """
    Пытаемся вытащить JSON-объект из строки:
    - сначала пробуем целиком
    - потом по первому '{' и последней '}'.
    """
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.S)
    text = (text or "").strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        pass

    l = text.find("{")
    r = text.rfind("}")
    if l == -1 or r == -1 or r <= l:
        return None

    candidate = text[l : r + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


SYSTEM_PROMPT = (
    "You parse OCR receipt lines for a budgeting app.\n"
    "Return ONE JSON object with keys: merchant, lang, items, raw_total_guess.\n"
    "Each item has: item_name_raw, price, category, bucket, confidence, norm_name.\n"
    "category must be one of "
    "[DAIRY, MEAT, VEGETABLES, FASTFOOD, COFFEE, PHARMACY, AUTO, "
    "BAKERY, ELECTRONICS, HOUSEHOLD, TAKEOUT, WANTS_OTHER, UNKNOWN].\n"
    "bucket must be one of [NEEDS, WANTS, UNKNOWN].\n"
    "If unsure, use category='UNKNOWN', bucket='UNKNOWN', confidence<=0.2.\n"
    "Ignore taxes, totals, payment lines, card numbers, approvals, points, addresses and dates as items.\n"
    "No explanations, no markdown, no reasoning. JSON only."
)


class LLMReceiptParser:
    def __init__(self, core: LLMCore | None = None) -> None:
        self.core = core or _llm_core

    def parse_and_classify_from_lines(
        self,
        *,
        lines: List[str],
        lang: str,
        debug: bool = False,
        max_tokens: int = 256,
    ) -> Tuple[LLMReceiptParseResult, Dict[str, Any]]:
        """
        На вход: сырые OCR-строки + lang.
        На выход: LLMReceiptParseResult (с category/bucket/conf/norm_name) + meta.
        """
        # лёгкая чистка, без завязки на язык
        clean: List[str] = []
        for s in lines:
            s = (s or "").strip()
            if not s:
                continue
            s = re.sub(r"\s+", " ", s)
            clean.append(s[:220])

        # ограничиваем количество строк, чтобы не раздувать контекст
        clean = clean[:200]

        if not clean:
            empty = LLMReceiptParseResult(
                merchant=None,
                lang=lang,
                items=[],
                raw_total_guess=None,
            )
            return empty, {}

        user_payload = {"lang": lang, "lines": clean}
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))},
        ]

        content, meta = self.core.chat(
            messages,
            temperature=0.0,
            max_tokens=max_tokens,
            no_think=True,
            format=None,        # полагаемся на промпт + _extract_json_obj
            return_meta=True,
            debug_raw=debug,
        )

        if debug:
            print("\n[LLM RECEIPT RAW RESPONSE]", repr(content), flush=True)
            print("[/LLM RECEIPT RAW RESPONSE]\n", flush=True)
            print("[LLM META]", meta, flush=True)

        data = _extract_json_obj(content)
        if not isinstance(data, dict):
            empty = LLMReceiptParseResult(
                merchant=None,
                lang=lang,
                items=[],
                raw_total_guess=None,
            )
            return empty, meta

        # --- merchant ---
        merchant = data.get("merchant")
        if isinstance(merchant, str):
            merchant = merchant.strip() or None
        else:
            merchant = None

        # --- lang ---
        lang_out = str(data.get("lang", lang)) or lang

        # --- raw_total_guess ---
        raw_total_guess = data.get("raw_total_guess", None)
        try:
            raw_total_guess_val: Optional[float] = (
                float(raw_total_guess) if raw_total_guess is not None else None
            )
        except Exception:
            raw_total_guess_val = None

        # --- items -> как dict'ы, Pydantic сам сделает модели ---
        out_items_raw: List[Dict[str, Any]] = []

        for it in (data.get("items") or []):
            if not isinstance(it, dict):
                continue

            name_raw = str(it.get("item_name_raw", "")).strip()
            if not name_raw:
                continue

            # price
            price = it.get("price", None)
            try:
                price_val: Optional[float] = float(price) if price is not None else None
            except Exception:
                price_val = None

            # category / bucket с нормализацией
            category_norm = _normalize_category(it.get("category", "UNKNOWN"))
            bucket_norm = _normalize_bucket(it.get("bucket", "UNKNOWN"))

            # confidence
            conf_raw = it.get("confidence", 0.2)
            try:
                conf_val = float(conf_raw)
            except Exception:
                conf_val = 0.2
            if conf_val < 0.0:
                conf_val = 0.0
            if conf_val > 1.0:
                conf_val = 1.0

            # norm_name
            norm = it.get("norm_name", None)
            if norm is not None:
                norm = str(norm).strip()
                if norm == "":
                    norm = None

            out_items_raw.append(
                {
                    "item_name_raw": name_raw,
                    "price": price_val,
                    "category": category_norm,
                    "bucket": bucket_norm,
                    "confidence": conf_val,
                    "norm_name": norm,
                }
            )

        result = LLMReceiptParseResult(
            merchant=merchant,
            lang=lang_out,
            items=out_items_raw,
            raw_total_guess=raw_total_guess_val,
        )
        return result, meta
