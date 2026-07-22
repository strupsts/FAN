from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.receipt import ReceiptDraft


class ReceiptExtractionError(RuntimeError):
    """Base error for receipt extraction failures."""


class InvalidReceiptImageError(ReceiptExtractionError):
    """Uploaded bytes are empty or are not a supported image."""


class ReceiptExtractorUnavailableError(ReceiptExtractionError):
    """External receipt extraction service is temporarily unavailable."""


class ReceiptExtractorResponseError(ReceiptExtractionError):
    """Receipt extractor returned an invalid or unusable response."""


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
