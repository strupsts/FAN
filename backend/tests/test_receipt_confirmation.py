from __future__ import annotations

import unittest
from uuid import UUID, uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.db.sqlalchemy_models import (
    Base,
    ReceiptRow,
    TrainingSampleRow,
)
from app.adapters.outbound.db.sqlalchemy_prediction_repository import (
    SQLAlchemyPredictionRepository,
)
from app.adapters.outbound.db.sqlalchemy_receipt_repository import (
    SQLAlchemyReceiptRepository,
)
from app.domain import ConfirmedReceipt, Money, ReceiptItem
from app.ports import (
    ReceiptDraftAlreadyConfirmedError,
    ReceiptDraftNotFoundError,
    ReceiptPredictionRecord,
)


class ReceiptConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:"
        )
        Base.metadata.create_all(bind=engine)

        self.session_factory = sessionmaker(
            bind=engine,
            class_=Session,
            expire_on_commit=False,
        )

        self.predictions = SQLAlchemyPredictionRepository(
            self.session_factory
        )
        self.receipts = SQLAlchemyReceiptRepository(
            self.session_factory
        )

        self.user_id = uuid4()
        self.draft_id = uuid4()

        self.prediction = ReceiptPredictionRecord(
            user_id=self.user_id,
            receipt_draft_id=self.draft_id,
            image_ref="local://receipts/test.jpg",
            extractor_name="qwen2.5-vl-7b-awq",
            model_output={
                "parsed": {
                    "merchant_name": "Predicted Store",
                    "total_amount": "10.00",
                }
            },
        )

        self.predictions.save_prediction(self.prediction)

    def _receipt(
        self,
        *,
        receipt_id: UUID | None = None,
    ) -> ConfirmedReceipt:
        return ConfirmedReceipt(
            id=receipt_id or uuid4(),
            user_id=self.user_id,
            merchant_name="Corrected Store",
            purchased_at=None,
            items=[
                ReceiptItem(
                    name="Corrected Item",
                    total_price=Money("12.00"),
                )
            ],
            subtotal=Money("12.00"),
            tax=Money("0.00"),
            total=Money("12.00"),
        )

    def _target_payload(self) -> dict:
        return {
            "merchant_name": "Corrected Store",
            "total": {
                "amount": "12.00",
                "currency": "CAD",
            },
        }

    def test_confirmation_is_persisted_with_training_sample(
        self,
    ) -> None:
        receipt = self._receipt()

        sample = self.receipts.confirm_prediction(
            user_id=self.user_id,
            receipt_draft_id=self.draft_id,
            receipt=receipt,
            target_payload=self._target_payload(),
        )

        loaded_prediction = self.predictions.get_prediction(
            user_id=self.user_id,
            receipt_draft_id=self.draft_id,
        )

        self.assertIsNotNone(loaded_prediction)
        assert loaded_prediction is not None

        self.assertEqual(
            loaded_prediction.confirmed_receipt_id,
            receipt.id,
        )
        self.assertIsNotNone(
            loaded_prediction.confirmed_at
        )
        self.assertEqual(
            sample.source_prediction_id,
            self.prediction.id,
        )
        self.assertEqual(
            sample.input_payload["extractor_name"],
            "qwen2.5-vl-7b-awq",
        )

        with self.session_factory() as session:
            receipt_count = session.scalar(
                select(func.count()).select_from(
                    ReceiptRow
                )
            )
            sample_count = session.scalar(
                select(func.count()).select_from(
                    TrainingSampleRow
                )
            )

        self.assertEqual(receipt_count, 1)
        self.assertEqual(sample_count, 1)

    def test_unknown_or_foreign_draft_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            ReceiptDraftNotFoundError
        ):
            self.receipts.confirm_prediction(
                user_id=uuid4(),
                receipt_draft_id=self.draft_id,
                receipt=self._receipt(),
                target_payload=self._target_payload(),
            )

    def test_duplicate_confirmation_is_rejected(
        self,
    ) -> None:
        self.receipts.confirm_prediction(
            user_id=self.user_id,
            receipt_draft_id=self.draft_id,
            receipt=self._receipt(),
            target_payload=self._target_payload(),
        )

        with self.assertRaises(
            ReceiptDraftAlreadyConfirmedError
        ):
            self.receipts.confirm_prediction(
                user_id=self.user_id,
                receipt_draft_id=self.draft_id,
                receipt=self._receipt(),
                target_payload=self._target_payload(),
            )

        with self.session_factory() as session:
            receipt_count = session.scalar(
                select(func.count()).select_from(
                    ReceiptRow
                )
            )
            sample_count = session.scalar(
                select(func.count()).select_from(
                    TrainingSampleRow
                )
            )

        self.assertEqual(receipt_count, 1)
        self.assertEqual(sample_count, 1)


if __name__ == "__main__":
    unittest.main()
