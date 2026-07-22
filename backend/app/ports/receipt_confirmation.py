from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.domain import ConfirmedReceipt


class ReceiptDraftNotFoundError(LookupError):
    """The requested draft does not exist for the current user."""


class ReceiptDraftAlreadyConfirmedError(RuntimeError):
    """The requested draft has already been confirmed."""


@dataclass(frozen=True)
class TrainingSample:
    user_id: UUID
    source_prediction_id: UUID
    input_payload: dict[str, Any]
    target_payload: dict[str, Any]
    id: UUID = field(default_factory=uuid4)
    is_sanitized: bool = False
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.input_payload:
            raise ValueError(
                "Training sample input_payload must not be empty"
            )

        if not self.target_payload:
            raise ValueError(
                "Training sample target_payload must not be empty"
            )


class ReceiptConfirmationPort(Protocol):
    def confirm_prediction(
        self,
        *,
        user_id: UUID,
        receipt_draft_id: UUID,
        receipt: ConfirmedReceipt,
        target_payload: dict[str, Any],
    ) -> TrainingSample:
        """
        Atomically persist a receipt, correction sample and
        prediction confirmation status.
        """
        ...
