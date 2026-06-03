from __future__ import annotations

from app.ports import OCRLine, OCRPort, OCRResult


class FakeOCRAdapter(OCRPort):
    def extract_text(self, image_ref: str) -> OCRResult:
        return OCRResult(
            full_text="FAKE STORE\nMILK 4.29\nBREAD 3.49\nTOTAL 7.78",
            lines=[
                OCRLine(text="FAKE STORE", confidence=0.99),
                OCRLine(text="MILK 4.29", confidence=0.95),
                OCRLine(text="BREAD 3.49", confidence=0.95),
                OCRLine(text="TOTAL 7.78", confidence=0.98),
            ],
            engine_name="fake_ocr",
        )
