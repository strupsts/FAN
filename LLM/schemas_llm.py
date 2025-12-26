from pydantic import BaseModel, Field
from typing import List, Optional, Literal

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


class LLMReceiptItem(BaseModel):
    item_name_raw: str
    price: Optional[float] = None

    # parse+classify поля (для parse-only могут быть None/UNKNOWN)
    category: Category = "UNKNOWN"
    bucket: Bucket = "UNKNOWN"
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    norm_name: Optional[str] = None


class LLMReceiptParseResult(BaseModel):
    merchant: Optional[str] = None
    lang: str = "en"
    items: List[LLMReceiptItem] = Field(default_factory=list)
    raw_total_guess: Optional[float] = None





class LLMReceiptItem(BaseModel):
    item_name_raw: str
    price: Optional[float] = None

    # добавь:
    category: Optional[str] = None
    bucket: Optional[str] = None
    confidence: Optional[float] = None
    norm_name: Optional[str] = None


class LLMReceiptItemPred(BaseModel):
    item_name_raw: str
    price: Optional[float] = None

    category: str
    bucket: str
    confidence: float = Field(ge=0.0, le=1.0)
    norm_name: str


class LLMReceiptParseAndClassifyResult(BaseModel):
    merchant: Optional[str] = None
    lang: str
    items: List[LLMReceiptItemPred] = []
    raw_total_guess: Optional[float] = None


