from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.application.commands import ConfirmReceiptCommand
from app.domain import ConfirmedReceipt, Money, ReceiptItem
from app.ports import (
    AnalyticsEvent,
    AnalyticsPort,
    ReceiptConfirmationPort,
)


class ConfirmReceiptUseCase:
    def __init__(
        self,
        confirmation_repository: ReceiptConfirmationPort,
        analytics: AnalyticsPort,
    ) -> None:
        self.confirmation_repository = confirmation_repository
        self.analytics = analytics

    def execute(
        self,
        command: ConfirmReceiptCommand,
    ) -> ConfirmedReceipt:
        confirmed_receipt = ConfirmedReceipt(
            id=uuid4(),
            user_id=command.user_id,
            merchant_name=command.merchant_name,
            purchased_at=command.purchased_at,
            items=command.items,
            total=command.total,
            subtotal=command.subtotal,
            tax=command.tax,
            image_ref=command.image_ref,
        )

        training_sample = (
            self.confirmation_repository.confirm_prediction(
                user_id=command.user_id,
                receipt_draft_id=command.draft_id,
                receipt=confirmed_receipt,
                target_payload=self._receipt_payload(
                    confirmed_receipt
                ),
            )
        )

        self.analytics.track(
            AnalyticsEvent(
                name="receipt_confirmed",
                user_id=command.user_id,
                properties={
                    "receipt_id": str(confirmed_receipt.id),
                    "draft_id": str(command.draft_id),
                    "training_sample_id": str(
                        training_sample.id
                    ),
                    "item_count": len(
                        confirmed_receipt.items
                    ),
                    "merchant_present": (
                        confirmed_receipt.merchant_name
                        is not None
                    ),
                },
            )
        )

        return confirmed_receipt

    def _receipt_payload(
        self,
        receipt: ConfirmedReceipt,
    ) -> dict[str, Any]:
        return {
            "merchant_name": receipt.merchant_name,
            "purchased_at": (
                receipt.purchased_at.isoformat()
                if receipt.purchased_at is not None
                else None
            ),
            "subtotal": self._money_payload(
                receipt.subtotal
            ),
            "tax": self._money_payload(receipt.tax),
            "total": self._money_payload(receipt.total),
            "items": [
                self._item_payload(item)
                for item in receipt.items
            ],
        }

    def _item_payload(
        self,
        item: ReceiptItem,
    ) -> dict[str, Any]:
        return {
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": self._money_payload(
                item.unit_price
            ),
            "total_price": self._money_payload(
                item.total_price
            ),
            "category": item.category.value,
            "bucket": item.bucket.value,
            "confidence": item.confidence,
        }

    def _money_payload(
        self,
        money: Money | None,
    ) -> dict[str, str] | None:
        if money is None:
            return None

        return {
            "amount": str(money.amount),
            "currency": money.currency,
        }
