from __future__ import annotations

from uuid import uuid4

from app.application.commands import ConfirmReceiptCommand
from app.domain.receipt import ConfirmedReceipt
from app.ports import AnalyticsEvent, AnalyticsPort, ReceiptRepositoryPort


class ConfirmReceiptUseCase:
    def __init__(
        self,
        receipt_repository: ReceiptRepositoryPort,
        analytics: AnalyticsPort,
    ) -> None:
        self.receipt_repository = receipt_repository
        self.analytics = analytics

    def execute(self, command: ConfirmReceiptCommand) -> ConfirmedReceipt:
        confirmed_receipt = ConfirmedReceipt(
            id=uuid4(),
            user_id=command.user_id,
            merchant_name=command.merchant_name,
            purchased_at=command.purchased_at,
            items=command.items,
            total=command.total,
            image_ref=command.image_ref,
        )

        self.receipt_repository.save_confirmed_receipt(confirmed_receipt)

        self.analytics.track(
            AnalyticsEvent(
                name="receipt_confirmed",
                user_id=command.user_id,
                properties={
                    "receipt_id": str(confirmed_receipt.id),
                    "draft_id": str(command.draft_id),
                    "item_count": len(confirmed_receipt.items),
                    "merchant_present": confirmed_receipt.merchant_name is not None,
                },
            )
        )

        return confirmed_receipt
