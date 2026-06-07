from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain import BudgetBucket, Category, ConfirmedReceipt, Money, ReceiptItem


class MoneyResponse(BaseModel):
    amount: str
    currency: str


class ReceiptItemRequest(BaseModel):
    name: str
    total_price_amount: str
    total_price_currency: str = "CAD"
    category: Category = Category.UNKNOWN
    bucket: BudgetBucket = BudgetBucket.UNKNOWN
    quantity: float | None = None
    unit_price_amount: str | None = None
    unit_price_currency: str = "CAD"
    confidence: float | None = Field(default=None, ge=0, le=1)

    def to_domain(self) -> ReceiptItem:
        unit_price = None
        if self.unit_price_amount is not None:
            unit_price = Money(
                amount=self.unit_price_amount,
                currency=self.unit_price_currency,
            )

        return ReceiptItem(
            name=self.name,
            total_price=Money(
                amount=self.total_price_amount,
                currency=self.total_price_currency,
            ),
            category=self.category,
            bucket=self.bucket,
            quantity=self.quantity,
            unit_price=unit_price,
            confidence=self.confidence,
        )


class ConfirmReceiptRequest(BaseModel):
    draft_id: UUID
    merchant_name: str | None = None
    purchased_at: datetime | None = None
    image_ref: str | None = None
    total_amount: str
    total_currency: str = "CAD"
    items: list[ReceiptItemRequest]


class ReceiptItemResponse(BaseModel):
    name: str
    total_price: MoneyResponse
    category: str
    bucket: str
    quantity: float | None = None
    confidence: float | None = None


class ReceiptResponse(BaseModel):
    id: str
    user_id: str
    merchant_name: str | None
    purchased_at: str | None
    total: MoneyResponse
    image_ref: str | None
    items: list[ReceiptItemResponse]


def receipt_to_response(receipt: ConfirmedReceipt) -> ReceiptResponse:
    return ReceiptResponse(
        id=str(receipt.id),
        user_id=str(receipt.user_id),
        merchant_name=receipt.merchant_name,
        purchased_at=receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        total=MoneyResponse(
            amount=str(receipt.total.amount),
            currency=receipt.total.currency,
        ),
        image_ref=receipt.image_ref,
        items=[
            ReceiptItemResponse(
                name=item.name,
                total_price=MoneyResponse(
                    amount=str(item.total_price.amount),
                    currency=item.total_price.currency,
                ),
                category=item.category.value,
                bucket=item.bucket.value,
                quantity=item.quantity,
                confidence=item.confidence,
            )
            for item in receipt.items
        ],
    )
