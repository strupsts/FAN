from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

from app.ports import ImageStoragePort, StoredImage


class LocalImageStorageAdapter(ImageStoragePort):
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save_receipt_image(
        self,
        user_id: UUID,
        image_bytes: bytes,
        original_filename: str | None = None,
        content_type: str | None = None,
    ) -> StoredImage:
        if not image_bytes:
            raise ValueError("image_bytes must not be empty")

        image_id = uuid4()
        extension = self._detect_extension(
            original_filename=original_filename,
            content_type=content_type,
        )

        relative_path = Path("users") / str(user_id) / str(image_id) / f"original{extension}"
        absolute_path = self.base_dir / relative_path

        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(image_bytes)

        image_ref = f"local://receipts/{relative_path.as_posix()}"

        return StoredImage(
            image_ref=image_ref,
            original_filename=original_filename,
            content_type=content_type,
        )

    def delete(self, image_ref: str) -> None:
        path = self.resolve_path(image_ref)
        if path.exists():
            path.unlink()

    def resolve_path(self, image_ref: str) -> Path:
        prefix = "local://receipts/"
        if not image_ref.startswith(prefix):
            raise ValueError("Unsupported image_ref format")

        relative_path = Path(image_ref.removeprefix(prefix))
        absolute_path = self.base_dir / relative_path

        try:
            absolute_path.resolve().relative_to(self.base_dir.resolve())
        except ValueError as error:
            raise ValueError("image_ref points outside storage directory") from error

        return absolute_path

    def _detect_extension(
        self,
        original_filename: str | None,
        content_type: str | None,
    ) -> str:
        if original_filename:
            suffix = Path(original_filename).suffix.lower()
            if suffix in {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}:
                return suffix

        content_type_to_extension = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/heic": ".heic",
            "image/heif": ".heif",
        }

        if content_type in content_type_to_extension:
            return content_type_to_extension[content_type]

        return ".bin"
