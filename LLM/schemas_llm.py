from datetime import datetime

from __future__ import annotations

from typing import Any, List, Optional, Literal, Dict
from pydantic import BaseModel, Field

# --- базовые типы для категорий/ведер ---

Category = Literal[
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
]

Bucket = Literal["NEEDS", "WANTS", "UNKNOWN"]


# --- Классификация одной позиции чека (LLM classifier) ---

class LLMItemRequest(BaseModel):
    merchant: Optional[str] = None
    item_name_raw: str
    price: Optional[float] = None
    lang: str = "en"


class LLMItemResponse(BaseModel):
    category: Category = "UNKNOWN"
    bucket: Bucket = "UNKNOWN"
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    norm_name: str


# --- Парсинг чека целиком (LLM receipt parser) ---

class LLMReceiptItem(BaseModel):
    item_name_raw: str
    price: Optional[float] = None
    category: Category = "UNKNOWN"
    bucket: Bucket = "UNKNOWN"
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    norm_name: Optional[str] = None


class LLMReceiptParseResult(BaseModel):
    merchant: Optional[str] = None
    lang: str = "en"
    items: List[LLMReceiptItem] = Field(default_factory=list)
    raw_total_guess: Optional[float] = None


# --- RQ job-схемы для очереди LLM receipt parser ---

class LlmReceiptJobCreateRequest(BaseModel):
    """
    Запрос от клиента на постановку задачи в очередь:
    пока только текстовые строки чека.
    """
    lang: str = "en"
    lines: List[str]
    max_tokens: int = Field(default=256, ge=32, le=1024)


class LlmReceiptJobEnqueueResponse(BaseModel):
    job_id: str


class LlmReceiptJobStatusResponse(BaseModel):
    id: str
    status: str
    enqueued_at: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
