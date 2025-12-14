from pydantic import BaseModel
from typing import List, Optional

class LLMItemRequest(BaseModel):
    """
    То, что наш backend будет готовить для LLM.

    Эти поля НЕ идут напрямую от фронта — мы сами их собираем
    для каждого товара.
    """
    merchant: str
    item_name_raw: str
    price: Optional[float] = None
    lang: str = "en" # lang from original source. Default is english

class LLMItemResponse(BaseModel):
    """
    То, что мы ожидаем получить от LLM-классификатора.
    Пока без жёстких enum'ов, просто строки.
    """
    category: str
    bucket: str
    confidence:  float 
    norm_name: str


class LLMReceiptItem(BaseModel): 
    """
    Одна позиция из чека после парсинга LLM.
    Тут merchant не дублируем — он общий для всего чека.
    """
    item_name_raw: str
    price: Optional[float] = None # None if model is unsure.

class LLMReceiptParseResult(BaseModel):
    """
    Итог парсинга текста/строк чека.
    """
    merchant: Optional[str] = None  # If couldn't find - None
    lang: str
    items: List[LLMReceiptItem]
    raw_total_guess: Optional[float] = None #best-guess for total if found

