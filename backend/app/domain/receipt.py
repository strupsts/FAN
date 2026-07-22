from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.category import BudgetBucket, Category
from app.domain.money import Money


@dataclass(frozen=True)
class ReceiptItem:
    name: str
    total_price: Money
    category: Category = Category.UNKNOWN
    bucket: BudgetBucket = BudgetBucket.UNKNOWN
    quantity: float | None = None
    unit_price: Money | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Receipt item name must not be empty")

        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")


@dataclass(frozen=True)
class ReceiptDraft:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    merchant_name: str | None = None
    purchased_at: datetime | None = None
    items: list[ReceiptItem] = field(default_factory=list)
    subtotal: Money | None = None
    tax: Money | None = None
    total: Money | None = None
    image_ref: str | None = None
    extractor_name: str | None = None

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("Receipt draft must contain at least one item")

    def items_total(self) -> Money:
        if not self.items:
            return Money.zero()

        result = Money.zero(self.items[0].total_price.currency)

        for item in self.items:
            result = result + item.total_price

        return result

    def has_total_mismatch(
        self,
        tolerance: Money | None = None,
    ) -> bool:
        if self.total is None:
            return False

        tolerance = tolerance or Money("0.05", self.total.currency)
        difference = self.items_total() - self.total

        return abs(difference.amount) > tolerance.amount


@dataclass(frozen=True)
class ConfirmedReceipt:
    id: UUID
    user_id: UUID
    merchant_name: str | None
    purchased_at: datetime | None
    items: list[ReceiptItem]
    total: Money
    subtotal: Money | None = None
    tax: Money | None = None
    image_ref: str | None = None
    confirmed_at: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError(
                "Confirmed receipt must contain at least one item"
            )

        if self.total.amount < 0:
            raise ValueError(
                "Confirmed receipt total cannot be negative"
            )
