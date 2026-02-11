"""
Compatibility shim.

Старый код делал:

    from schemas import PredictRequest, ...

А реальные модели лежат в API.schemas.
Этот модуль просто реэкспортирует их.
"""

from API.schemas import *  # noqa: F401,F403
from pydantic import BaseModel
from typing import List, Optional



"""
# [ocr_text.py] OCR
"""

class OcrPreviewRequest(BaseModel):
    raw_text: str
    lang: Optional[str] = None # "en", "ru", "uk" etc 

class OcrPreviewItem(BaseModel):
    item_name_raw: str
    price: float
    ocr_conf: float # confidence OCR, placeholder atm

class OcrPreviewResponse(BaseModel):
    merchant: str
    lang: Optional[str] = None
    items: List[OcrPreviewItem]
    raw_total_guess: Optional[float] = None # Rough estimation TOTAL from the text

# OCR PREDICT (OCR + ML)

class OcrPredictedItem(BaseModel):
    item_name_raw: str
    price: float

    category: str
    bucket: str
    conf: float

class OcrPredictResponse(BaseModel):
    merchant: str
    lang: Optional[str] = None
    items: List[OcrPredictedItem]
    raw_total_guess: Optional[float] = None

# OCR CONFIRM (for the receipt list table and training samples table in DB)

class OcrConfirmedItem(BaseModel):
    item_name_raw: str
    price: float

    # what model was thinking
    model_category: str
    model_bucket: str
    model_conf: float

    # what the user decided
    final_category: str
    final_bucket: str

class OcrConfirmRequest(BaseModel):        
    # stuff that front sending to server after confirming receipt
    merchant: str
    lang: Optional[str] = None
    items: List[OcrConfirmedItem]

class OcrConfirmResponse(BaseModel):
    # respond from the server, things we saved 
    receipt_id: int
    items_saved: int    


    """
    [main.py] API 
    """

class PredictRequest(BaseModel): 
    merchant: str
    item_name: str

class PredictResponse(BaseModel): 
    merchant: str
    item_name: str
    category: str
    bucket: str
    confidence: float

class PredictManyRequest(BaseModel):
    item: list[PredictRequest]

class PredictManyResponse(BaseModel):
    item: list[PredictResponse]        

  # [Pydantic-models] Receipt
class ReceiptItemRequest(BaseModel):
    merchant: str
    item_name: str
    price: float 

class ReceiptItemResponse(BaseModel):
    merchant: str
    item_name: str
    price: float

    # главная версия, которую видит юзер (LLM или логрега)
    category: str
    bucket: str
    confidence: float

    # от логрегression — чисто для анализа/отладки
    lr_category: Optional[str] = None
    lr_bucket: Optional[str] = None
    lr_confidence: Optional[float] = None

    # от LLM — тоже для анализа/отладки
    llm_category: Optional[str] = None
    llm_bucket: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_norm_name: Optional[str] = None

class ReceiptSummary(BaseModel):
    total: float
    by_bucket: dict[str, float]  # например {"NEEDS": 85.5, "WANTS": 23.2}
    by_category: dict[str, float]  # {"DAIRY": 10.5, "FASTFOOD": 18.0, ...}

class ReceiptRequest(BaseModel):
    items: list[ReceiptItemRequest]

class ReceiptResponse(BaseModel):
    receipt_id: int
    items: list[ReceiptItemResponse]
    summary: ReceiptSummary


# [Pydantic-models] GET req for list of all receipts
class ReceiptShort(BaseModel):
    id: int
    merchant: str
    created_at: str
    total_amount: float
    source: str    

#  [Pydantic-models] GET req for detail receipt and his items
class ReceiptItemDetail(BaseModel):
    id: int
    merchant: str
    item_name: str
    price: float
    category: str
    bucket: str
    confidence: float


class ReceiptDetail(BaseModel):
    id: int
    merchant: str
    created_at: str
    total_amount: float
    source: str
    items: list[ReceiptItemDetail]

# [Pydantic-models] Response for totals request

class SpendingSummary(BaseModel):
    total: float
    by_bucket: dict[str, float]
    by_category: dict[str, float]    
