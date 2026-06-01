from __future__ import annotations

from typing import Protocol

from app.domain.receipt import ReceiptDraft
from app.ports.ocr import OCRResult


class ReceiptParserPort(Protocol):
    def parse_receipt(self, ocr_result: OCRResult, image_ref: str | None = None) -> ReceiptDraft:
        """Parse OCR result into a structured receipt draft."""
        ...
