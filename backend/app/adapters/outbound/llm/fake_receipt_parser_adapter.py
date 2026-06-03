from __future__ import annotations

from app.domain import BudgetBucket, Category, Money, ReceiptDraft, ReceiptItem
from app.ports import OCRResult, ReceiptParserPort


class FakeReceiptParserAdapter(ReceiptParserPort):
    def parse_receipt(self, ocr_result: OCRResult, image_ref: str | None = None) -> ReceiptDraft:
        return ReceiptDraft(
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
            raw_ocr_text=ocr_result.full_text,
            parser_name="fake_receipt_parser",
        )
