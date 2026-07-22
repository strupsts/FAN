from __future__ import annotations

import logging
from dataclasses import replace

from app.application.commands import ProcessReceiptCommand
from app.domain.receipt import ReceiptDraft
from app.ports import (
    AnalyticsEvent,
    AnalyticsPort,
    ImageStoragePort,
    PredictionRepositoryPort,
    ReceiptDraftExtractorPort,
    ReceiptPredictionRecord,
)


logger = logging.getLogger(__name__)


class ProcessReceiptUseCase:
    def __init__(
        self,
        image_storage: ImageStoragePort,
        extractor: ReceiptDraftExtractorPort,
        prediction_repository: PredictionRepositoryPort,
        analytics: AnalyticsPort,
    ) -> None:
        self.image_storage = image_storage
        self.extractor = extractor
        self.prediction_repository = prediction_repository
        self.analytics = analytics

    def execute(
        self,
        command: ProcessReceiptCommand,
    ) -> ReceiptDraft:
        stored_image = self.image_storage.save_receipt_image(
            user_id=command.user_id,
            image_bytes=command.image_bytes,
            original_filename=command.original_filename,
            content_type=command.content_type,
        )

        try:
            extraction = self.extractor.extract_receipt(
                image_bytes=command.image_bytes,
                original_filename=command.original_filename,
                content_type=command.content_type,
                image_ref=stored_image.image_ref,
            )

            receipt_draft = replace(
                extraction.draft,
                user_id=command.user_id,
                image_ref=stored_image.image_ref,
                extractor_name=extraction.extractor_name,
            )

            prediction = ReceiptPredictionRecord(
                user_id=command.user_id,
                receipt_draft_id=receipt_draft.id,
                image_ref=stored_image.image_ref,
                extractor_name=extraction.extractor_name,
                model_output=extraction.model_output,
            )

            self.prediction_repository.save_prediction(prediction)
        except Exception:
            try:
                self.image_storage.delete(stored_image.image_ref)
            except Exception:
                logger.exception(
                    "Failed to delete receipt image after "
                    "receipt processing failure",
                    extra={
                        "image_ref": stored_image.image_ref,
                    },
                )

            raise

        self.analytics.track(
            AnalyticsEvent(
                name="receipt_processed",
                user_id=command.user_id,
                properties={
                    "prediction_id": str(prediction.id),
                    "extractor_name": extraction.extractor_name,
                    "item_count": len(receipt_draft.items),
                    "has_total_mismatch":
                        receipt_draft.has_total_mismatch(),
                },
            )
        )

        return receipt_draft
