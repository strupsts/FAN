from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class ReceiptPredictionRecord:
    user_id: UUID
    receipt_draft_id: UUID
    image_ref: str
    extractor_name: str
    model_output: dict[str, Any] | None = None
    confirmed_receipt_id: UUID | None = None
    confirmed_at: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.image_ref.strip():
            raise ValueError(
                "Prediction image_ref must not be empty"
            )

        if not self.extractor_name.strip():
            raise ValueError(
                "Prediction extractor_name must not be empty"
            )

        has_receipt = self.confirmed_receipt_id is not None
        has_timestamp = self.confirmed_at is not None

        if has_receipt != has_timestamp:
            raise ValueError(
                "Prediction confirmation ID and timestamp "
                "must be set together"
            )


class PredictionRepositoryPort(Protocol):
    def save_prediction(
        self,
        prediction: ReceiptPredictionRecord,
    ) -> None:
        """Persist a raw model prediction for audit and training."""

    def get_prediction(
        self,
        *,
        user_id: UUID,
        receipt_draft_id: UUID,
    ) -> ReceiptPredictionRecord | None:
        """Find a user's prediction by receipt draft ID."""
