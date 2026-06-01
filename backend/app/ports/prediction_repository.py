from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ReceiptPredictionRecord:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    receipt_draft_id: UUID | None = None
    image_ref: str | None = None
    ocr_engine: str | None = None
    parser_name: str | None = None
    raw_ocr_text: str | None = None
    model_output: dict[str, Any] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class PredictionRepositoryPort(Protocol):
    def save_prediction(self, prediction: ReceiptPredictionRecord) -> None:
        """Save raw OCR/model prediction for audit, evals, and future training."""
        ...
