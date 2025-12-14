from __future__ import annotations

import json
from typing import List, Optional

from LLM.schemas_llm import LLMReceiptParseResult, LLMItemRequest, LLMReceiptItem
from .llm_core import LLMCore

_llm_core = LLMCore()



class LLMReceiptParser: 
    """
    LLM-слой, который из строк OCR делает структурированный чек.
    Вход: список строк + lang.
    Выход: LLMReceiptParseResult.
    """

    def __init__(self, core: LLMCore | None = None) -> None:
        self.core = core or _llm_core

    def parse_from_lines(self, *, lines: List[str], lang: str) -> LLMReceiptParseResult:
        """
        Главный метод: кормим LLM список строк чека и язык.
        """
        system_prompt = (
            "You are a strict JSON-only receipt parser for a personal finance app.\n"
            "You receive OCR text of a receipt as a list of lines (strings).\n"
            "Your task is to extract:\n"
            "  - merchant: store name (e.g. 'Walmart', 'Shoppers', 'Пятёрочка')\n"
            "  - items: list of { item_name_raw, price }\n"
            "  - raw_total_guess: numeric total of the receipt if you can estimate it.\n"
            "\n"
            "Rules:\n"
            "  - Ignore loyalty points, card numbers, references, approval codes.\n"
            "  - Ignore taxes/fees *as separate lines* in items; only real purchases.\n"
            "  - prices are floats (use dot as decimal separator).\n"
            "  - If you are not sure about price, you may omit that item or set price=null.\n"
            "  - If you are not sure about merchant, set merchant=null.\n"
            "\n"
            "You MUST respond with ONLY ONE JSON object of this schema:\n"
            "{\n"
            "  \"merchant\": string | null,\n"
            "  \"lang\": string,  // original language code, like 'en', 'ru', 'uk'\n"
            "  \"items\": [\n"
            "    { \"item_name_raw\": string, \"price\": number | null }\n"
            "  ],\n"
            "  \"raw_total_guess\": number | null\n"
            "}\n"
            "No extra text, no markdown, no comments, ONLY JSON.\n"
        )

        user_payload = {
            "lang": lang,
            "lines": lines
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": "Here is the OCR result of the receipt:\n"
                            + json.dumps(user_payload, ensure_ascii=False),
            },
        ]

        # 3) выстрел в LLM
        # Ответ может быть немного длиннее, чем у классификатора (много items),
        # поэтому max_tokens делаем с запасом.
        content = self.core.chat(messages, temperature=0.1, max_tokens=2768)


        # можно на время дебага оставить print:
        print("\n[LLM RECEIPT RAW RESPONSE]")
        print(repr(content))
        print("[/LLM RECEIPT RAW RESPONSE]\n")

        # 4) Парсим JSON
        data = json.loads(content)

        # 5) Нормализуем поля и собираем LLMREceiptParseResult
        merchant = data.get("merchant")
        if merchant is not None:
            merchant = str(merchant).strip() or None

        out_items: List[LLMReceiptItem] = []
        for item in data.get("items", []):
            name_raw = str(item.get("item_name_raw", "")).strip()
            if not name_raw:
                continue

            price_val: Optional[float]
            if "price" in item and item["price"] is not None:
                try: 
                    price_val = float(item["price"])
                except(Exception):
                    price_val = None
            else: 
                price_val = None

            out_items.append(LLMReceiptItem(item_name_raw=name_raw, price=price_val))    
        raw_total_guess_val: Optional[float] = None
        if data.get("raw_total_guess") is not None:
            try:
                raw_total_guess_val = float(data["raw_total_guess"])
            except Exception:
                raw_total_guess_val = None                  

        # 6) возвращаем pydantic - модель
        return LLMReceiptParseResult(
            merchant = merchant,
            lang = lang,
            items = out_items,
            raw_total_guess=raw_total_guess_val
        )
