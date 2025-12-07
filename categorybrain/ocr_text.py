import re

from categorybrain.categorybrain_ml import CategoryBrainML


from typing import List

from schemes import (
    OcrPreviewItem,
    OcrPreviewResponse,
    OcrPredictedItem,
    OcrPredictResponse,
)


SERVICE_WORDS = [
    "total",
    "subtotal",
    "gst",
    "tax",
    "visa",
    "mastercard",
    "thank you",
    "change",
]


PRICE_RE = re.compile(r"(\d+[.,]\d{2})")


def extract_price(line: str) -> float | None:
    """
    Ищем цену в строке.
    Возвращаем float или None, если цены нет.
    """
    matches = PRICE_RE.findall(line)
    if not matches:
        return None

    raw = matches[-1]  # берём ПОСЛЕДНЕЕ совпадение в строке
    raw = raw.replace(",", ".")  # приводим к 3.99
    try:
        return float(raw)
    except ValueError:
        return None


def parse_item_line(line: str) -> tuple[str, float] | None:
    """
    Разбирает строку вида 'Milk 2L 3.99' в (item_name_raw, price).
    Если цену найти не удалось — возвращает None.
    """
    price = extract_price(line)
    if price is None:
        return None

    # отрезаем цену справа: делим строку на 2 части по последнему пробелу
    # 'Milk 2L 3.99' -> ['Milk 2L', '3.99']
    parts = line.rsplit(" ", 1)
    item_part = parts[0].strip()

    return item_part, price


def parse_receipt_text(raw_text: str, lang: str | None = None) -> OcrPreviewResponse:
    """
    Простенький парсер текстового чека:
    - первая непустая строка -> merchant
    - остальные строки -> пытаемся превратить в (item_name_raw, price)
    - игнорируем служебные строки (total/tax/etc.)
    """
    # 1) Разбиваем на строки и чистим пробелы
    lines = [ln.strip() for ln in raw_text.splitlines()]
    # убираем пустые строки
    lines = [ln for ln in lines if ln]

    if not lines:
        raise ValueError("Receipt text is empty")

    # 2) merchant - just first line
    merchant = lines[0]
    item_lines = lines[1:]

    items: list[OcrPreviewItem] = []
    raw_total_guess: float | None = None

    for line in item_lines:
        low = line.lower()

        # 3) пробуем вытащить total, есть
        if "total" in low:
            maybe_total = extract_price(line)
            if maybe_total is not None:
                raw_total_guess = maybe_total
            # даже если это total, не рассматриваем как товар
            continue

        # 4) отфильтровываем явный мусор
        if any(word in low for word in SERVICE_WORDS):
            continue

        parsed = parse_item_line(line)
        if parsed is None:
            # Couldnt find a price - skip the row
            continue

        item_name_raw, price = parsed
        items.append(
            OcrPreviewItem(
                item_name_raw=item_name_raw,
                price=price,
                ocr_conf=0.9,  # placeholder atm
            )
        )

        # 5) if results no items found - error
    if not items:
        raise ValueError("Couldnt find of items")

    return OcrPreviewResponse(
        merchant=merchant, lang=lang, items=items, raw_total_guess=raw_total_guess
    )


def predict_on_preview(
    preview: OcrPreviewResponse, brain: CategoryBrainML
) -> OcrPredictResponse:
    """
    Берём результат parse_receipt_text и прогоняем через CategoryBrainML:
    merchant + item_name -> category, bucket, conf.
    """
    predicted_items: List[OcrPredictedItem] = []

    for item in preview.items:
        # 1) Делаем предсказание по (merchant, item_name_raw)
        cat, bucket, conf = brain.predict(
            merchant=preview.merchant,
            item_name=item.item_name_raw,
        )

        # 2) Упаковываем одну строку в pydantic-модель
        predicted_items.append(
            OcrPredictedItem(
                item_name_raw=item.item_name_raw,
                price=item.price,
                category=cat,
                bucket=bucket,
                conf=conf,
            )
        )

    # 3) Возвращаем общий ответ по всему чеку
    return OcrPredictResponse(
        merchant=preview.merchant,
        lang=preview.lang,
        items=predicted_items,
        raw_total_guess=preview.raw_total_guess,
    )
