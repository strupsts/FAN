from __future__ import annotations

from uuid import UUID

from app.domain.receipt import ConfirmedReceipt
from app.ports import ReceiptRepositoryPort


class GetReceiptHistoryUseCase:
    def __init__(self, receipt_repository: ReceiptRepositoryPort) -> None:
        self.receipt_repository = receipt_repository

    def execute(self, user_id: UUID) -> list[ConfirmedReceipt]:
        return self.receipt_repository.list_receipts(user_id=user_id)
