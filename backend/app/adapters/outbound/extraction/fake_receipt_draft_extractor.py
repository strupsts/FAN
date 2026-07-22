from __future__ import annotations

from app.domain import BudgetBucket, Category, Money, ReceiptDraft, ReceiptItem
from app.ports.receipt_draft_extractor import (
    ReceiptDraftExtractorPort,
    ReceiptExtractionResult,
)


class FakeReceiptDraftExtractorAdapter(ReceiptDraftExtractorPort):
    extractor_name = "fake_receipt_draft_extractor"

    def extract_receipt(
        self,
        *,
        image_bytes: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
        image_ref: str | None = None,
    ) -> ReceiptExtractionResult:
        draft = ReceiptDraft(
            merchant_name="Fake Store",
            items=[
                ReceiptItem(
                    name="Milk",
                    total_price=Money("4.29"),
                    category=Category.GROCERIES,
                    bucket=BudgetBucket.NEEDS,
                    confidence=0.90,
                ),
                ReceiptItem(
                    name="Bread",
                    total_price=Money("3.49"),
                    category=Category.GROCERIES,
                    bucket=BudgetBucket.NEEDS,
                    confidence=0.90,
                ),
            ],
            total=Money("7.78"),
            image_ref=image_ref,
            parser_name=self.extractor_name,
        )

        model_output = {
            "merchant_name": "Fake Store",
            "total_amount": "7.78",
            "currency": "CAD",
            "items": [
                {
                    "name": "Milk",
                    "total_price_amount": "4.29",
                    "category": "groceries",
                    "bucket": "needs",
                    "confidence": 0.90,
                },
                {
                    "name": "Bread",
                    "total_price_amount": "3.49",
                    "category": "groceries",
                    "bucket": "needs",
                    "confidence": 0.90,
                },
            ],
        }

        return ReceiptExtractionResult(
            draft=draft,
            extractor_name=self.extractor_name,
            model_output=model_output,
        )
