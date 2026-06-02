from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain.summary import SpendingSummary
from app.ports import AnalyticsEvent, AnalyticsPort, ReceiptRepositoryPort


class GetSpendingSummaryUseCase:
    def __init__(
        self,
        receipt_repository: ReceiptRepositoryPort,
        analytics: AnalyticsPort,
    ) -> None:
        self.receipt_repository = receipt_repository
        self.analytics = analytics

    def execute(self, user_id: UUID, from_date: date, to_date: date) -> SpendingSummary:
        summary = self.receipt_repository.get_spending_summary(
            user_id=user_id,
            from_date=from_date,
            to_date=to_date,
        )

        self.analytics.track(
            AnalyticsEvent(
                name="summary_viewed",
                user_id=user_id,
                properties={
                    "from_date": from_date.isoformat(),
                    "to_date": to_date.isoformat(),
                    "category_count": len(summary.by_category),
                    "merchant_count": len(summary.by_merchant),
                },
            )
        )

        return summary
