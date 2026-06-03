from __future__ import annotations

from datetime import date
from uuid import UUID

from app.domain import ConfirmedReceipt, Money, SpendingSummary
from app.ports import (
    PredictionRepositoryPort,
    ReceiptPredictionRecord,
    ReceiptRepositoryPort,
    TrainingSample,
    TrainingSampleRepositoryPort,
)


class InMemoryReceiptRepository(ReceiptRepositoryPort):
    def __init__(self) -> None:
        self.receipts: list[ConfirmedReceipt] = []

    def save_confirmed_receipt(self, receipt: ConfirmedReceipt) -> None:
        self.receipts.append(receipt)

    def list_receipts(self, user_id: UUID) -> list[ConfirmedReceipt]:
        return [receipt for receipt in self.receipts if receipt.user_id == user_id]

    def get_spending_summary(
        self,
        user_id: UUID,
        from_date: date,
        to_date: date,
    ) -> SpendingSummary:
        user_receipts = self.list_receipts(user_id)

        total = Money.zero()
        for receipt in user_receipts:
            total = total + receipt.total

        return SpendingSummary(
            from_date=from_date,
            to_date=to_date,
            total_spent=total,
            by_category=[],
            by_merchant=[],
        )


class InMemoryPredictionRepository(PredictionRepositoryPort):
    def __init__(self) -> None:
        self.predictions: list[ReceiptPredictionRecord] = []

    def save_prediction(self, prediction: ReceiptPredictionRecord) -> None:
        self.predictions.append(prediction)


class InMemoryTrainingSampleRepository(TrainingSampleRepositoryPort):
    def __init__(self) -> None:
        self.samples: list[TrainingSample] = []

    def save_training_sample(self, sample: TrainingSample) -> None:
        self.samples.append(sample)
