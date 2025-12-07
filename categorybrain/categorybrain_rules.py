from __future__ import annotations
from typing import Dict, List, Tuple
import re


KEYWORDS: Dict[str, List[str]] = {
    "DAIRY": ["milk", "c e", "yogurt", "butter"],
    "MEAT": ["chicken", "beef", "pork"],
    "VEGETABLES": ["banana", "apple", "tomato", "potato", "lettuce"],
    "BAKERY": ["bread", "bun", "baguette"],
    "FASTFOOD": ["burger", "big mac", "fries", "combo", "mc", "kfc", "pizza"],
    "COFFEE": ["latte", "coffee", "americano", "espresso"],
    "PHARMACY": ["ibuprofen", "acetaminophen", "vitamin"],
    "AUTO": ["motor oil", "5w-30", "coolant"],
    "HOUSEHOLD": ["toilet paper", "detergent", "soap"],
    "ELECTRONICS": ["usb-c", "cable", "ssd", "gpu"],
    "TAKEOUT": ["pizza", "sushi", "wings"],
    "WANTS_OTHER": ["energy drink", "chocolate", "snack"],
}

MERCHANT_HINT: Dict[str, str] = {
    "mcdonalds": "FASTFOOD",
    "pizza hut": "TAKEOUT",
    "starbucks": "COFFEE",
    "tim hortons": "COFFEE",
}


BUCKET_MAP: Dict[str, str] = {
    "DAIRY": "NEEDS",
    "MEAT": "NEEDS",
    "VEGETABLES": "NEEDS",
    "BAKERY": "NEEDS",
    "HOUSEHOLD": "NEEDS",
    "PHARMACY": "NEEDS",
    "AUTO": "NEEDS",
    "FASTFOOD": "WANTS",
    "TAKEOUT": "WANTS",
    "COFFEE": "WANTS",
    "ELECTRONICS": "WANTS",  # на старте так; потом можно тоньше
    "WANTS_OTHER": "WANTS",
    "UNCAT": "WANTS",  # по умолчанию нераспозн. считаем WANTS (лучше “консервативно”)
}


def _normalize(text: str) -> str:

    t = text.lower()
    #  Оставим буквы, цифры и пробелы. Остальное заменим на пробелы
    t = re.sub(r"[^a-z0-9\s\-\+]", " ", t)

    # схлопнем многократные проблеы
    t = re.sub(r"\s+", " ", t)
    return t


def _score_keywords(text: str, keywords: List[str]) -> int:
    """
    Считаем, сколько ключевых слов встретилось в тексте (грубая метрика).
    """
    score = 0
    for kw in keywords:
        if kw in text:
            score += 1
    return score


def predict_category(merchant: str, item_name: str) -> Tuple[str, str, float]:
    """
    Вход: merchant, item_name
    Выход: (category, bucket, confidence[0..1])
    Логика v0: подсказка по мерчанту → подсчёт совпадений ключевых слов → выбор лучшего.
    """
    m = _normalize(merchant)
    n = _normalize(item_name)

    # 1) Подсказка по мерчанту — даём +2 балла соответствующей категории
    hint_scores: Dict[str, int] = {}
    for hint, cat in MERCHANT_HINT.items():
        if hint in m:
            hint_scores[cat] = hint_scores.get(cat, 0) + 2

    # 2) Подсчёт по ключевым словам
    scores: Dict[str, int] = dict(hint_scores)  # стартуем с учётом мерчанта
    for cat, kws in KEYWORDS.items():
        scores[cat] = scores.get(cat, 0) + _score_keywords(n, kws)

    # 3) Выбор категории с макс. баллом
    best_cat = "UNCAT"
    best_score = 0
    for cat, sc in scores.items():
        if sc > best_score:
            best_cat, best_score = cat, sc

    # 4) Уверенность: простая функция от счёта (0 → 0.0, 1 → 0.6, >=2 → 0.9)
    if best_score <= 0:
        confidence = 0.0
    elif best_score == 1:
        confidence = 0.6
    else:
        confidence = 0.9

    bucket = BUCKET_MAP.get(best_cat, "WANTS")
    return best_cat, bucket, confidence


def category_to_bucket(category: str) -> str:
    "Аккуратно получить ведро  по категории (или Wants по умолчанию)"
    return BUCKET_MAP.get(category, "WANTS")
