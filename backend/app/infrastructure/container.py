from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.adapters.outbound.analytics.in_memory_analytics_adapter import InMemoryAnalyticsAdapter
from app.adapters.outbound.db.in_memory_repositories import (
    InMemoryPredictionRepository,
    InMemoryTrainingSampleRepository,
)
from app.adapters.outbound.db.sqlalchemy_receipt_repository import SQLAlchemyReceiptRepository
from app.adapters.outbound.llm.fake_receipt_parser_adapter import FakeReceiptParserAdapter
from app.adapters.outbound.ocr.fake_ocr_adapter import FakeOCRAdapter
from app.adapters.outbound.privacy.noop_privacy_adapter import NoopPrivacyAdapter
from app.adapters.outbound.storage.local_image_storage import LocalImageStorageAdapter
from app.application import (
    ConfirmReceiptUseCase,
    GetReceiptHistoryUseCase,
    GetSpendingSummaryUseCase,
    ProcessReceiptUseCase,
)
from app.infrastructure.database import create_db_engine, create_session_factory


@dataclass
class AppContainer:
    image_storage: LocalImageStorageAdapter
    ocr: FakeOCRAdapter
    parser: FakeReceiptParserAdapter
    receipt_repository: SQLAlchemyReceiptRepository
    prediction_repository: InMemoryPredictionRepository
    training_sample_repository: InMemoryTrainingSampleRepository
    analytics: InMemoryAnalyticsAdapter
    privacy: NoopPrivacyAdapter

    process_receipt_use_case: ProcessReceiptUseCase
    confirm_receipt_use_case: ConfirmReceiptUseCase
    get_receipt_history_use_case: GetReceiptHistoryUseCase
    get_spending_summary_use_case: GetSpendingSummaryUseCase


def build_container() -> AppContainer:
    project_root = Path(__file__).resolve().parents[3]
    receipt_storage_dir = project_root / "storage" / "receipts"

    engine = create_db_engine()
    session_factory = create_session_factory(engine)

    image_storage = LocalImageStorageAdapter(base_dir=receipt_storage_dir)
    ocr = FakeOCRAdapter()
    parser = FakeReceiptParserAdapter()
    receipt_repository = SQLAlchemyReceiptRepository(session_factory=session_factory)
    prediction_repository = InMemoryPredictionRepository()
    training_sample_repository = InMemoryTrainingSampleRepository()
    analytics = InMemoryAnalyticsAdapter()
    privacy = NoopPrivacyAdapter()

    process_receipt_use_case = ProcessReceiptUseCase(
        image_storage=image_storage,
        ocr=ocr,
        parser=parser,
        prediction_repository=prediction_repository,
        analytics=analytics,
    )

    confirm_receipt_use_case = ConfirmReceiptUseCase(
        receipt_repository=receipt_repository,
        analytics=analytics,
    )

    get_receipt_history_use_case = GetReceiptHistoryUseCase(
        receipt_repository=receipt_repository,
    )

    get_spending_summary_use_case = GetSpendingSummaryUseCase(
        receipt_repository=receipt_repository,
        analytics=analytics,
    )

    return AppContainer(
        image_storage=image_storage,
        ocr=ocr,
        parser=parser,
        receipt_repository=receipt_repository,
        prediction_repository=prediction_repository,
        training_sample_repository=training_sample_repository,
        analytics=analytics,
        privacy=privacy,
        process_receipt_use_case=process_receipt_use_case,
        confirm_receipt_use_case=confirm_receipt_use_case,
        get_receipt_history_use_case=get_receipt_history_use_case,
        get_spending_summary_use_case=get_spending_summary_use_case,
    )
