from __future__ import annotations

from typing import Optional

from schemas_llm import LLMItemRequest, LLMItemResponse

class LLMClassifier: 
    """
    Обёртка над LLM-классификатором.

    Сейчас это ЗАГЛУШКА:
    - никаких реальных нейросетей,
    - просто примитивные правила по ключевым словам.

    Потом мы заменим внутренности на вызов Qwen2.5,
    но сигнатура методов останется той же.
    """
    def _init(self) -> None: 
        # Здесь потом можно будет:
        # - подключаться к локальному LLM-серверу,
        # - хранить настройки промпта,
        # - кэшировать результаты и т.п.
        self.name = "llm_stub_v0"

    def classify_item(self, req: LLMItemRequest) -> LLMItemResponse:
        """
        Основной метод: принимает LLMItemRequest, возвращает LLMItemResponse.
        Сейчас внутри — тупой keyword-based "ИИ".
        """
        text = f"{req.merchant} {req.item_name_raw}".lower()       

         # --- очень грубые эвристики по словам ---
        if any(k in text for k in ["milk", "cheese", "yogurt", "cream"]):
            category = "DAIRY"
        elif any(k in text for k in ["chicken", "beef", "pork", "steak", "sausage"]):
            category = "MEAT"
        elif any(k in text for k in ["banana", "apple", "carrot", "tomato", "cucumber", "potato"]):
            category = "VEGETABLES"
        elif any(k in text for k in ["pizza", "burger", "big mac", "combo", "burrito"]):
            category = "FASTFOOD"
        elif any(k in text for k in ["latte", "coffee", "americano", "cappuccino"]):
            category = "COFFEE"
        elif any(k in text for k in ["ibuprofen", "acetaminophen", "vitamin", "syrup"]):
            category = "PHARMACY"
        elif any(k in text for k in ["oil", "tire", "wiper", "washer", "car"]):
            category = "AUTO"
        elif any(k in text for k in ["bread", "muffin", "croissant", "cookie", "cake"]):
            category = "BAKERY"
        elif any(k in text for k in ["hdmi", "usb", "keyboard", "mouse", "earbuds", "webcam"]):
            category = "ELECTRONICS"
        elif any(k in text for k in ["detergent", "garbage bags", "soap", "cleaner", "sponge"]):
            category = "HOUSEHOLD"
        elif any(k in text for k in ["pizza hut", "dominos", "subway", "doordash", "skip", "chipotle"]):
            category = "TAKEOUT"
        elif any(k in text for k in ["chips", "chocolate", "energy drink", "slurpee", "ice cream"]):
            category = "WANTS_OTHER"
        else:
            category = "UNKNOWN"

        # --- грубое правило для бакета ---
        if category in ["DAIRY", "MEAT", "VEGETABLES", "PHARMACY", "HOUSEHOLD", "AUTO"]:
            bucket = "NEEDS"
        elif category in ["FASTFOOD", "COFFEE", "BAKERY", "ELECTRONICS", "TAKEOUT", "WANTS_OTHER"]:
            bucket = "WANTS"
        else:
            bucket = "UNKNOWN"

        # "уверенность" тоже сделаем грубой:
        if category == "UNKNOWN":
            confidence = 0.2
        else:
            confidence = 0.7

        # norm_name можно пока просто привести к нормальному виду
        norm_name = req.item_name_raw.strip()

        return LLMItemResponse(
            category=category,
            bucket=bucket,
            confidence=confidence,
            norm_name=norm_name,
        )