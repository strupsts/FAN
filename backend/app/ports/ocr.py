from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OCRLine:
    text: str
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("OCR line text must not be empty")

        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("OCR confidence must be between 0 and 1")


@dataclass(frozen=True)
class OCRResult:
    full_text: str
    lines: list[OCRLine]
    engine_name: str

    def __post_init__(self) -> None:
        if not self.engine_name.strip():
            raise ValueError("OCR engine_name must not be empty")


class OCRPort(Protocol):
    def extract_text(self, image_ref: str) -> OCRResult:
        """Extract text from a stored receipt image."""
        ...
