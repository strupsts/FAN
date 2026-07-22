from __future__ import annotations

import unittest
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.db.sqlalchemy_models import Base
from app.adapters.outbound.db.sqlalchemy_prediction_repository import (
    SQLAlchemyPredictionRepository,
)
from app.ports import ReceiptPredictionRecord


class SQLAlchemyPredictionRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(bind=engine)

        session_factory = sessionmaker(
            bind=engine,
            class_=Session,
            expire_on_commit=False,
        )

        self.repository = SQLAlchemyPredictionRepository(
            session_factory=session_factory
        )

    def test_saves_and_loads_prediction_by_user_and_draft(self) -> None:
        user_id = uuid4()
        draft_id = uuid4()

        prediction = ReceiptPredictionRecord(
            user_id=user_id,
            receipt_draft_id=draft_id,
            image_ref="local://receipts/test/original.jpg",
            extractor_name="qwen2.5-vl-7b-awq",
            model_output={
                "parsed": {
                    "merchant_name": "Test Store",
                    "total_amount": "12.34",
                }
            },
        )

        self.repository.save_prediction(prediction)

        loaded = self.repository.get_prediction(
            user_id=user_id,
            receipt_draft_id=draft_id,
        )

        self.assertIsNotNone(loaded)
        assert loaded is not None

        self.assertEqual(loaded.id, prediction.id)
        self.assertEqual(loaded.user_id, user_id)
        self.assertEqual(loaded.receipt_draft_id, draft_id)
        self.assertEqual(
            loaded.extractor_name,
            "qwen2.5-vl-7b-awq",
        )
        self.assertEqual(
            loaded.model_output,
            prediction.model_output,
        )

    def test_does_not_return_another_users_prediction(self) -> None:
        draft_id = uuid4()

        prediction = ReceiptPredictionRecord(
            user_id=uuid4(),
            receipt_draft_id=draft_id,
            image_ref="local://receipts/test/original.jpg",
            extractor_name="qwen2.5-vl-7b-awq",
        )

        self.repository.save_prediction(prediction)

        loaded = self.repository.get_prediction(
            user_id=uuid4(),
            receipt_draft_id=draft_id,
        )

        self.assertIsNone(loaded)


if __name__ == "__main__":
    unittest.main()
