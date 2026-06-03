from __future__ import annotations

from dataclasses import dataclass

from app.adapters.outbound.analytics.in_memory_analytics_adapter import InMemoryAnalyticsAdapter
from app.adapters.outbound.db.in_memory_repositories import (
    InMemoryPredictionRepository,
    InMemoryReceiptRepository,
    InMemoryTrainingSampleRepository,
)
from app.adapters.outbound.llm.fake_receipt_parser_adapter import FakeReceiptParserAdapter
from app.adapters.outbound.ocr.fake_ocr_adapter import FakeOCRAdapter
from app.adapters.outbound.privacy.noop_privacy_adapter import NoopPrivacyAdapter
from app.adapters.outbound.storage.in_memory_image_storage import InMemoryImageStorageAdapter
from app.application import (
    ConfirmReceiptUseCase,
    GetReceiptHistoryUseCase,
    GetSpendingSummaryUseCase,
    ProcessReceiptUseCase,
)


@dataclass
class AppContainer:
    image_storage: InMemoryImageStorageAdapter
    ocr: FakeOCRAdapter
    parser: FakeReceiptParserAdapter
    receipt_repository: InMemoryReceiptRepository
    prediction_repository: InMemoryPredictionRepository
    training_sample_repository: InMemoryTrainingSampleRepository
    analytics: InMemoryAnalyticsAdapter
    privacy: NoopPrivacyAdapter

    process_receipt_use_case: ProcessReceiptUseCase
    confirm_receipt_use_case: ConfirmReceiptUseCase
    get_receipt_history_use_case: GetReceiptHistoryUseCase
    get_spending_summary_use_case: GetSpendingSummaryUseCase


def build_container() -> AppContainer:
    image_storage = InMemoryImageStorageAdapter()
    ocr = FakeOCRAdapter()
    parser = FakeReceiptParserAdapter()
    receipt_repository = InMemoryReceiptRepository()
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
