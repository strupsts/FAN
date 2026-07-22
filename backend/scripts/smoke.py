from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.adapters.outbound.analytics.in_memory_analytics_adapter import (
    InMemoryAnalyticsAdapter,
)
from app.adapters.outbound.db.in_memory_repositories import (
    InMemoryPredictionRepository,
)
from app.adapters.outbound.extraction import (
    FakeReceiptDraftExtractorAdapter,
)
from app.adapters.outbound.storage.local_image_storage import (
    LocalImageStorageAdapter,
)
from app.application import (
    ProcessReceiptCommand,
    ProcessReceiptUseCase,
)


def main() -> None:
    with TemporaryDirectory() as temporary_dir:
        image_storage = LocalImageStorageAdapter(
            base_dir=Path(temporary_dir)
        )
        extractor = FakeReceiptDraftExtractorAdapter()
        prediction_repository = InMemoryPredictionRepository()
        analytics = InMemoryAnalyticsAdapter()

        use_case = ProcessReceiptUseCase(
            image_storage=image_storage,
            extractor=extractor,
            prediction_repository=prediction_repository,
            analytics=analytics,
        )

        command = ProcessReceiptCommand(
            user_id=uuid4(),
            image_bytes=b"fake image bytes",
            original_filename="receipt.jpg",
            content_type="image/jpeg",
        )

        draft = use_case.execute(command)

        print(draft.merchant_name)
        print(draft.total)
        print([item.name for item in draft.items])
        print([event.name for event in analytics.events])
        print(len(prediction_repository.predictions))
        print(draft.image_ref)


if __name__ == "__main__":
    main()
