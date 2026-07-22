from __future__ import annotations

import unittest
from datetime import datetime
from uuid import uuid4

from app.adapters.inbound.api.routes.receipt_schemas import (
    receipt_draft_to_response,
    receipt_to_response,
)
from app.domain import (
    BudgetBucket,
    Category,
    ConfirmedReceipt,
    Money,
    ReceiptDraft,
    ReceiptItem,
)


class ReceiptReviewContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = ReceiptItem(
            name="Test Item",
            quantity=2,
            unit_price=Money("3.00"),
            total_price=Money("6.00"),
            category=Category.GROCERIES,
            bucket=BudgetBucket.NEEDS,
            confidence=0.95,
        )

        self.purchased_at = datetime(
            2026,
            7,
            22,
            9,
            30,
            0,
        )

    def test_draft_response_contains_reviewable_fields(self) -> None:
        draft = ReceiptDraft(
            merchant_name="Test Store",
            purchased_at=self.purchased_at,
            items=[self.item],
            subtotal=Money("6.00"),
            tax=Money("0.30"),
            total=Money("6.30"),
            image_ref="local://receipts/test.jpg",
            extractor_name="qwen2.5-vl-7b-awq",
        )

        payload = receipt_draft_to_response(draft).model_dump(
            mode="json"
        )

        self.assertEqual(
            payload["purchased_at"],
            "2026-07-22T09:30:00",
        )
        self.assertEqual(payload["subtotal"]["amount"], "6.00")
        self.assertEqual(payload["tax"]["amount"], "0.30")
        self.assertEqual(
            payload["extractor_name"],
            "qwen2.5-vl-7b-awq",
        )
        self.assertEqual(
            payload["items"][0]["unit_price"]["amount"],
            "3.00",
        )

    def test_confirmed_response_preserves_financial_fields(self) -> None:
        receipt = ConfirmedReceipt(
            id=uuid4(),
            user_id=uuid4(),
            merchant_name="Test Store",
            purchased_at=self.purchased_at,
            items=[self.item],
            subtotal=Money("6.00"),
            tax=Money("0.30"),
            total=Money("6.30"),
        )

        payload = receipt_to_response(receipt).model_dump(
            mode="json"
        )

        self.assertEqual(payload["subtotal"]["amount"], "6.00")
        self.assertEqual(payload["tax"]["amount"], "0.30")
        self.assertEqual(
            payload["items"][0]["unit_price"]["amount"],
            "3.00",
        )


if __name__ == "__main__":
    unittest.main()
