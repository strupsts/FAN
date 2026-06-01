from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class StoredImage:
    image_ref: str
    original_filename: str | None = None
    content_type: str | None = None

    def __post_init__(self) -> None:
        if not self.image_ref.strip():
            raise ValueError("image_ref must not be empty")


class ImageStoragePort(Protocol):
    def save_receipt_image(
        self,
        user_id: UUID,
        image_bytes: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
    ) -> StoredImage:
        """Store receipt image and return internal image reference."""
        ...

    def delete(self, image_ref: str) -> None:
        """Delete stored image by reference."""
        ...
