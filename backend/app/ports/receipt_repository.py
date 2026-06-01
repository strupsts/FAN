from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from app.domain.receipt import ConfirmedReceipt
from app.domain.summary import SpendingSummary


class ReceiptRepositoryPort(Protocol):
    def save_confirmed_receipt(self, receipt: ConfirmedReceipt) -> None:
        """Persist confirmed user receipt."""
        ...

    def list_receipts(self, user_id: UUID) -> list[ConfirmedReceipt]:
        """List confirmed receipts for a user."""
        ...

    def get_spending_summary(
        self,
        user_id: UUID,
        from_date: date,
        to_date: date,
    ) -> SpendingSummary:
        """Return spending summary for date range."""
        ...
