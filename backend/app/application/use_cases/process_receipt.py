from __future__ import annotations

from app.application.commands import ProcessReceiptCommand
from app.domain.receipt import ReceiptDraft
from app.ports import (
    AnalyticsEvent,
    AnalyticsPort,
    ImageStoragePort,
    OCRPort,
    PredictionRepositoryPort,
    ReceiptParserPort,
    ReceiptPredictionRecord,
)


class ProcessReceiptUseCase:
    def __init__(
        self,
        image_storage: ImageStoragePort,
        ocr: OCRPort,
        parser: ReceiptParserPort,
        prediction_repository: PredictionRepositoryPort,
        analytics: AnalyticsPort,
    ) -> None:
        self.image_storage = image_storage
        self.ocr = ocr
        self.parser = parser
        self.prediction_repository = prediction_repository
        self.analytics = analytics

    def execute(self, command: ProcessReceiptCommand) -> ReceiptDraft:
        stored_image = self.image_storage.save_receipt_image(
            user_id=command.user_id,
            image_bytes=command.image_bytes,
            original_filename=command.original_filename,
            content_type=command.content_type,
        )

        ocr_result = self.ocr.extract_text(stored_image.image_ref)

        receipt_draft = self.parser.parse_receipt(
            ocr_result=ocr_result,
            image_ref=stored_image.image_ref,
        )

        prediction = ReceiptPredictionRecord(
            user_id=command.user_id,
            receipt_draft_id=receipt_draft.id,
            image_ref=stored_image.image_ref,
            ocr_engine=ocr_result.engine_name,
            parser_name=receipt_draft.parser_name,
            raw_ocr_text=ocr_result.full_text,
            model_output=None,
        )
        self.prediction_repository.save_prediction(prediction)

        self.analytics.track(
            AnalyticsEvent(
                name="receipt_processed",
                user_id=command.user_id,
                properties={
                    "ocr_engine": ocr_result.engine_name,
                    "parser_name": receipt_draft.parser_name,
                    "item_count": len(receipt_draft.items),
                    "has_total_mismatch": receipt_draft.has_total_mismatch(),
                },
            )
        )

        return receipt_draft
