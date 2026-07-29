from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.adapters.outbound.analytics.in_memory_analytics_adapter import InMemoryAnalyticsAdapter
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
    QwenVLMReceiptDraftExtractorAdapter,
)
from app.adapters.outbound.privacy.noop_privacy_adapter import NoopPrivacyAdapter
from app.adapters.outbound.storage.local_image_storage import LocalImageStorageAdapter
from app.application import (
    ConfirmReceiptUseCase,
    GetReceiptHistoryUseCase,
    GetSpendingSummaryUseCase,
    ProcessReceiptUseCase,
)
from app.infrastructure.config import get_settings
from app.infrastructure.database import create_db_engine, create_session_factory
from app.ports import ReceiptDraftExtractorPort, UserRepositoryPort


@dataclass
class AppContainer:
    image_storage: LocalImageStorageAdapter
    extractor: ReceiptDraftExtractorPort
    receipt_repository: SQLAlchemyReceiptRepository
    prediction_repository: SQLAlchemyPredictionRepository
    user_repository: UserRepositoryPort
    analytics: InMemoryAnalyticsAdapter
    privacy: NoopPrivacyAdapter

    process_receipt_use_case: ProcessReceiptUseCase
    confirm_receipt_use_case: ConfirmReceiptUseCase
    get_receipt_history_use_case: GetReceiptHistoryUseCase
    get_spending_summary_use_case: GetSpendingSummaryUseCase


def build_container() -> AppContainer:
    settings = get_settings()
    project_root = Path(__file__).resolve().parents[3]
    receipt_storage_dir = project_root / "storage" / "receipts"

    engine = create_db_engine()
    session_factory = create_session_factory(engine)

    image_storage = LocalImageStorageAdapter(base_dir=receipt_storage_dir)

    if settings.receipt_extraction_provider == "vlm":
        extractor: ReceiptDraftExtractorPort = QwenVLMReceiptDraftExtractorAdapter(
            base_url=settings.vlm_base_url,
            api_key=settings.vlm_api_key,
            model=settings.vlm_model,
            timeout_seconds=settings.vlm_timeout_seconds,
            temperature=settings.vlm_temperature,
            max_tokens=settings.vlm_max_tokens,
        )
    else:
        extractor = FakeReceiptDraftExtractorAdapter()

    receipt_repository = SQLAlchemyReceiptRepository(
        session_factory=session_factory
    )
    prediction_repository = SQLAlchemyPredictionRepository(
        session_factory=session_factory
    )
    user_repository = SQLAlchemyUserRepository(
        session_factory=session_factory
    )
    analytics = InMemoryAnalyticsAdapter()
    privacy = NoopPrivacyAdapter()

    process_receipt_use_case = ProcessReceiptUseCase(
        image_storage=image_storage,
        extractor=extractor,
        prediction_repository=prediction_repository,
        analytics=analytics,
    )

    confirm_receipt_use_case = ConfirmReceiptUseCase(
        confirmation_repository=receipt_repository,
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
        extractor=extractor,
        receipt_repository=receipt_repository,
        prediction_repository=prediction_repository,
        user_repository=user_repository,
        analytics=analytics,
        privacy=privacy,
        process_receipt_use_case=process_receipt_use_case,
        confirm_receipt_use_case=confirm_receipt_use_case,
        get_receipt_history_use_case=get_receipt_history_use_case,
        get_spending_summary_use_case=get_spending_summary_use_case,
    )
