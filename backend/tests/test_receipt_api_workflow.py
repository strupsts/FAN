from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.inbound.api.dependencies import (
    get_container,
    get_current_user_id,
)
from app.adapters.outbound.analytics.in_memory_analytics_adapter import (
    InMemoryAnalyticsAdapter,
)
from app.adapters.outbound.db.sqlalchemy_models import (
    Base,
    TrainingSampleRow,
    UserRow,
)
from app.adapters.outbound.db.sqlalchemy_prediction_repository import (
    SQLAlchemyPredictionRepository,
)
from app.adapters.outbound.db.sqlalchemy_receipt_repository import (
    SQLAlchemyReceiptRepository,
)
from app.adapters.outbound.db.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.adapters.outbound.extraction import (
    FakeReceiptDraftExtractorAdapter,
)
from app.adapters.outbound.privacy.noop_privacy_adapter import (
    NoopPrivacyAdapter,
)
from app.adapters.outbound.storage.local_image_storage import (
    LocalImageStorageAdapter,
)
from app.application import (
    ConfirmReceiptUseCase,
    GetCurrentUserProfileUseCase,
    GetReceiptHistoryUseCase,
    GetSpendingSummaryUseCase,
    ProcessReceiptUseCase,
    SetUserPreferencesUseCase,
)
from app.infrastructure.container import AppContainer
from app.main import create_app


class ReceiptAPIWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.user_id = uuid4()
        self.temporary_directory = tempfile.TemporaryDirectory()

        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)

        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

        with self.session_factory() as session:
            session.add(
                UserRow(id=self.user_id)
            )
            session.commit()

        receipt_repository = SQLAlchemyReceiptRepository(
            self.session_factory
        )
        prediction_repository = SQLAlchemyPredictionRepository(
            self.session_factory
        )
        user_repository = SQLAlchemyUserRepository(
            self.session_factory
        )
        analytics = InMemoryAnalyticsAdapter()

        image_storage = LocalImageStorageAdapter(
            base_dir=Path(self.temporary_directory.name)
        )
        extractor = FakeReceiptDraftExtractorAdapter()

        process_use_case = ProcessReceiptUseCase(
            image_storage=image_storage,
            extractor=extractor,
            prediction_repository=prediction_repository,
            analytics=analytics,
        )
        confirm_use_case = ConfirmReceiptUseCase(
            confirmation_repository=receipt_repository,
            analytics=analytics,
        )

        container = AppContainer(
            image_storage=image_storage,
            extractor=extractor,
            receipt_repository=receipt_repository,
            prediction_repository=prediction_repository,
            user_repository=user_repository,
            analytics=analytics,
            privacy=NoopPrivacyAdapter(),
            get_current_user_profile_use_case=(
                GetCurrentUserProfileUseCase(
                    user_repository=user_repository,
                )
            ),
            set_user_preferences_use_case=(
                SetUserPreferencesUseCase(
                    user_repository=user_repository,
                )
            ),
            process_receipt_use_case=process_use_case,
            confirm_receipt_use_case=confirm_use_case,
            get_receipt_history_use_case=GetReceiptHistoryUseCase(
                receipt_repository=receipt_repository
            ),
            get_spending_summary_use_case=GetSpendingSummaryUseCase(
                receipt_repository=receipt_repository,
                analytics=analytics,
            ),
        )

        self.app = create_app()
        self.app.dependency_overrides[get_container] = lambda: container
        self.app.dependency_overrides[
            get_current_user_id
        ] = lambda: self.user_id

        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()
        self.engine.dispose()
        self.temporary_directory.cleanup()

    def _process_receipt(self) -> dict:
        response = self.client.post(
            "/api/receipts/process",
            files={
                "file": (
                    "receipt.jpg",
                    b"\xff\xd8\xfffake-receipt-image",
                    "image/jpeg",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        return response.json()

    def _confirm_payload(self, draft: dict) -> dict:
        return {
            "draft_id": draft["id"],
            "merchant_name": "Corrected Store",
            "purchased_at": "2026-07-22T09:30:00",
            "image_ref": draft["image_ref"],
            "subtotal_amount": "7.78",
            "subtotal_currency": "CAD",
            "tax_amount": "0.00",
            "tax_currency": "CAD",
            "total_amount": draft["total"]["amount"],
            "total_currency": draft["total"]["currency"],
            "items": [
                {
                    "name": item["name"],
                    "total_price_amount": (
                        item["total_price"]["amount"]
                    ),
                    "total_price_currency": (
                        item["total_price"]["currency"]
                    ),
                    "category": item["category"],
                    "bucket": item["bucket"],
                    "quantity": item["quantity"],
                    "unit_price_amount": (
                        item["unit_price"]["amount"]
                        if item["unit_price"] is not None
                        else None
                    ),
                    "unit_price_currency": (
                        item["unit_price"]["currency"]
                        if item["unit_price"] is not None
                        else item["total_price"]["currency"]
                    ),
                    "confidence": item["confidence"],
                }
                for item in draft["items"]
            ],
        }

    def test_process_confirm_history_and_summary(self) -> None:
        draft = self._process_receipt()

        confirm_response = self.client.post(
            "/api/receipts/confirm",
            json=self._confirm_payload(draft),
        )

        self.assertEqual(confirm_response.status_code, 200)

        confirmed = confirm_response.json()

        self.assertEqual(
            confirmed["merchant_name"],
            "Corrected Store",
        )
        self.assertEqual(
            confirmed["subtotal"]["amount"],
            "7.78",
        )

        history_response = self.client.get(
            "/api/receipts/history"
        )

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_response.json()), 1)
        self.assertEqual(
            history_response.json()[0]["id"],
            confirmed["id"],
        )

        summary_response = self.client.get(
            "/api/receipts/summary",
            params={
                "from_date": "2026-07-22",
                "to_date": "2026-07-22",
            },
        )

        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(
            summary_response.json()["total_spent"]["amount"],
            "7.78",
        )

        with self.session_factory() as session:
            sample_count = session.scalar(
                select(func.count()).select_from(
                    TrainingSampleRow
                )
            )

        self.assertEqual(sample_count, 1)

    def test_unknown_draft_returns_404(self) -> None:
        draft = self._process_receipt()
        payload = self._confirm_payload(draft)
        payload["draft_id"] = str(uuid4())

        response = self.client.post(
            "/api/receipts/confirm",
            json=payload,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["detail"],
            "Receipt draft was not found.",
        )

    def test_duplicate_confirmation_returns_409(self) -> None:
        draft = self._process_receipt()
        payload = self._confirm_payload(draft)

        first_response = self.client.post(
            "/api/receipts/confirm",
            json=payload,
        )
        second_response = self.client.post(
            "/api/receipts/confirm",
            json=payload,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 409)

    def test_android_origin_preflight_is_allowed(
        self,
    ) -> None:
        response = self.client.options(
            "/api/receipts/confirm",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "content-type"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers[
                "access-control-allow-origin"
            ],
            "http://localhost",
        )

    def test_invalid_requests_return_422(self) -> None:
        empty_image_response = self.client.post(
            "/api/receipts/process",
            files={
                "file": (
                    "receipt.jpg",
                    b"",
                    "image/jpeg",
                )
            },
        )

        self.assertEqual(
            empty_image_response.status_code,
            422,
        )

        draft = self._process_receipt()
        payload = self._confirm_payload(draft)
        payload["items"] = []

        empty_items_response = self.client.post(
            "/api/receipts/confirm",
            json=payload,
        )

        self.assertEqual(
            empty_items_response.status_code,
            422,
        )


if __name__ == "__main__":
    unittest.main()
