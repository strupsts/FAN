from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.db.sqlalchemy_models import (
    ReceiptPredictionRow,
)
from app.ports import (
    PredictionRepositoryPort,
    ReceiptPredictionRecord,
)


class SQLAlchemyPredictionRepository(PredictionRepositoryPort):
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.session_factory = session_factory

    def save_prediction(
        self,
        prediction: ReceiptPredictionRecord,
    ) -> None:
        with self.session_factory() as session:
            session.add(self._prediction_to_row(prediction))
            session.commit()

    def get_prediction(
        self,
        *,
        user_id: UUID,
        receipt_draft_id: UUID,
    ) -> ReceiptPredictionRecord | None:
        with self.session_factory() as session:
            statement = select(ReceiptPredictionRow).where(
                ReceiptPredictionRow.user_id == user_id,
                ReceiptPredictionRow.receipt_draft_id
                == receipt_draft_id,
            )

            row = session.scalar(statement)

            if row is None:
                return None

            return self._row_to_prediction(row)

    def _prediction_to_row(
        self,
        prediction: ReceiptPredictionRecord,
    ) -> ReceiptPredictionRow:
        return ReceiptPredictionRow(
            id=prediction.id,
            user_id=prediction.user_id,
            receipt_draft_id=prediction.receipt_draft_id,
            image_ref=prediction.image_ref,
            extractor_name=prediction.extractor_name,
            confirmed_receipt_id=(
                prediction.confirmed_receipt_id
            ),
            confirmed_at=prediction.confirmed_at,
            model_output=prediction.model_output,
            created_at=prediction.created_at,
        )

    def _row_to_prediction(
        self,
        row: ReceiptPredictionRow,
    ) -> ReceiptPredictionRecord:
        return ReceiptPredictionRecord(
            id=row.id,
            user_id=row.user_id,
            receipt_draft_id=row.receipt_draft_id,
            image_ref=row.image_ref,
            extractor_name=row.extractor_name,
            confirmed_receipt_id=row.confirmed_receipt_id,
            confirmed_at=row.confirmed_at,
            model_output=row.model_output,
            created_at=row.created_at,
        )
