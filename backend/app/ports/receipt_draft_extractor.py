from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.receipt import ReceiptDraft


@dataclass(frozen=True)
class ReceiptExtractionResult:
    draft: ReceiptDraft
    extractor_name: str
    model_output: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.extractor_name.strip():
            raise ValueError("extractor_name must not be empty")


class ReceiptDraftExtractorPort(Protocol):
    def extract_receipt(
        self,
        *,
        image_bytes: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
        image_ref: str | None = None,
    ) -> ReceiptExtractionResult:
        """Extract a structured receipt draft directly from an image."""
        ...
