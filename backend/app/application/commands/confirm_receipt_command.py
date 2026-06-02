from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.money import Money
from app.domain.receipt import ReceiptItem


@dataclass(frozen=True)
class ConfirmReceiptCommand:
    user_id: UUID
    draft_id: UUID
    items: list[ReceiptItem]
    total: Money
    merchant_name: str | None = None
    purchased_at: datetime | None = None
    image_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("Confirmed receipt must contain at least one item")
