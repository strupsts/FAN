from __future__ import annotations

from uuid import UUID, uuid4

from app.ports import ImageStoragePort, StoredImage


class InMemoryImageStorageAdapter(ImageStoragePort):
    def __init__(self) -> None:
        self.images: dict[str, bytes] = {}

    def save_receipt_image(
        self,
        user_id: UUID,
        image_bytes: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
    ) -> StoredImage:
        image_ref = f"in-memory://users/{user_id}/receipts/{uuid4()}"

        self.images[image_ref] = image_bytes

        return StoredImage(
            image_ref=image_ref,
            original_filename=original_filename,
            content_type=content_type,
        )

    def delete(self, image_ref: str) -> None:
        self.images.pop(image_ref, None)
