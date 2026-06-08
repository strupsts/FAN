from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain import (
    BudgetBucket,
    Category,
    ConfirmedReceipt,
    Money,
    ReceiptDraft,
    ReceiptItem,
    SpendingSummary,
)


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


class ReceiptDraftResponse(BaseModel):
    id: str
    merchant_name: str | None
    total: MoneyResponse | None
    image_ref: str | None
    parser_name: str | None
    items: list[ReceiptItemResponse]


class ReceiptResponse(BaseModel):
    id: str
    user_id: str
    merchant_name: str | None
    purchased_at: str | None
    total: MoneyResponse
    image_ref: str | None
    items: list[ReceiptItemResponse]


class CategorySpendingResponse(BaseModel):
    category: str
    total: MoneyResponse
    transaction_count: int


class MerchantSpendingResponse(BaseModel):
    merchant_name: str
    total: MoneyResponse
    transaction_count: int


class SpendingSummaryResponse(BaseModel):
    from_date: str
    to_date: str
    total_spent: MoneyResponse
    by_category: list[CategorySpendingResponse]
    by_merchant: list[MerchantSpendingResponse]


def money_to_response(money: Money) -> MoneyResponse:
    return MoneyResponse(
        amount=str(money.amount),
        currency=money.currency,
    )


def item_to_response(item: ReceiptItem) -> ReceiptItemResponse:
    return ReceiptItemResponse(
        name=item.name,
        total_price=money_to_response(item.total_price),
        category=item.category.value,
        bucket=item.bucket.value,
        quantity=item.quantity,
        confidence=item.confidence,
    )


def receipt_draft_to_response(draft: ReceiptDraft) -> ReceiptDraftResponse:
    return ReceiptDraftResponse(
        id=str(draft.id),
        merchant_name=draft.merchant_name,
        total=money_to_response(draft.total) if draft.total else None,
        image_ref=draft.image_ref,
        parser_name=draft.parser_name,
        items=[item_to_response(item) for item in draft.items],
    )


def receipt_to_response(receipt: ConfirmedReceipt) -> ReceiptResponse:
    return ReceiptResponse(
        id=str(receipt.id),
        user_id=str(receipt.user_id),
        merchant_name=receipt.merchant_name,
        purchased_at=receipt.purchased_at.isoformat() if receipt.purchased_at else None,
        total=money_to_response(receipt.total),
        image_ref=receipt.image_ref,
        items=[item_to_response(item) for item in receipt.items],
    )


def summary_to_response(summary: SpendingSummary) -> SpendingSummaryResponse:
    return SpendingSummaryResponse(
        from_date=summary.from_date.isoformat(),
        to_date=summary.to_date.isoformat(),
        total_spent=money_to_response(summary.total_spent),
        by_category=[
            CategorySpendingResponse(
                category=item.category.value,
                total=money_to_response(item.total),
                transaction_count=item.transaction_count,
            )
            for item in summary.by_category
        ],
        by_merchant=[
            MerchantSpendingResponse(
                merchant_name=item.merchant_name,
                total=money_to_response(item.total),
                transaction_count=item.transaction_count,
            )
            for item in summary.by_merchant
        ],
    )
