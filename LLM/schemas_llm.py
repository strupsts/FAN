from pydantic import BaseModel
from typing import Optional

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
        