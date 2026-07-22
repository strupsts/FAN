from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from app.adapters.outbound.extraction import QwenVLMReceiptDraftExtractorAdapter
from app.adapters.outbound.storage.local_image_storage import LocalImageStorageAdapter
from app.application import ProcessReceiptCommand, ProcessReceiptUseCase
from app.ports import (
    InvalidReceiptImageError,
    ReceiptExtractorUnavailableError,
    StoredImage,
)


class RecordingImageStorage:
    def __init__(self) -> None:
        self.deleted_refs: list[str] = []

    def save_receipt_image(
        self,
        user_id,
        image_bytes,
        original_filename=None,
        content_type=None,
    ) -> StoredImage:
        return StoredImage(
            image_ref="local://receipts/test/original.jpg",
            original_filename=original_filename,
            content_type=content_type,
        )

    def delete(self, image_ref: str) -> None:
        self.deleted_refs.append(image_ref)


class FailingExtractor:
    def extract_receipt(self, **kwargs):
        raise ReceiptExtractorUnavailableError("VLM is unavailable")


class RecordingPredictionRepository:
    def __init__(self) -> None:
        self.predictions = []

    def save_prediction(self, prediction) -> None:
        self.predictions.append(prediction)


class RecordingAnalytics:
    def __init__(self) -> None:
        self.events = []

    def track(self, event) -> None:
        self.events.append(event)


class ProcessReceiptFailureTests(unittest.TestCase):
    def test_deletes_stored_image_when_extraction_fails(self) -> None:
        storage = RecordingImageStorage()
        predictions = RecordingPredictionRepository()
        analytics = RecordingAnalytics()

        use_case = ProcessReceiptUseCase(
            image_storage=storage,
            extractor=FailingExtractor(),
            prediction_repository=predictions,
            analytics=analytics,
        )

        command = ProcessReceiptCommand(
            user_id=uuid4(),
            image_bytes=b"fake bytes",
            original_filename="receipt.jpg",
            content_type="image/jpeg",
        )

        with self.assertRaises(ReceiptExtractorUnavailableError):
            use_case.execute(command)

        self.assertEqual(
            storage.deleted_refs,
            ["local://receipts/test/original.jpg"],
        )
        self.assertEqual(predictions.predictions, [])
        self.assertEqual(analytics.events, [])


class QwenVLMValidationTests(unittest.TestCase):
    def test_rejects_non_image_bytes_before_request(self) -> None:
        extractor = QwenVLMReceiptDraftExtractorAdapter(
            base_url="http://127.0.0.1:8002/v1",
            api_key="test",
            model="test-model",
        )

        with self.assertRaises(InvalidReceiptImageError):
            extractor.extract_receipt(
                image_bytes=b"this is not an image",
                original_filename="receipt.jpg",
                content_type="image/jpeg",
            )


class LocalImageStorageDeleteTests(unittest.TestCase):
    def test_delete_removes_image_and_empty_image_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_dir:
            storage = LocalImageStorageAdapter(
                base_dir=Path(temporary_dir)
            )

            stored = storage.save_receipt_image(
                user_id=uuid4(),
                image_bytes=b"image bytes",
                original_filename="receipt.jpg",
                content_type="image/jpeg",
            )

            image_path = storage.resolve_path(stored.image_ref)
            image_directory = image_path.parent

            self.assertTrue(image_path.exists())

            storage.delete(stored.image_ref)

            self.assertFalse(image_path.exists())
            self.assertFalse(image_directory.exists())


if __name__ == "__main__":
    unittest.main()
