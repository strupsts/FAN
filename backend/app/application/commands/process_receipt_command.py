from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ProcessReceiptCommand:
    user_id: UUID
    image_bytes: bytes
    original_filename: str | None = None
    content_type: str | None = None

    def __post_init__(self) -> None:
        if not self.image_bytes:
            raise ValueError("image_bytes must not be empty")
