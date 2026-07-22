from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.adapters.outbound.db.sqlalchemy_models import (
    ReceiptItemRow,
    ReceiptPredictionRow,
    ReceiptRow,
    TrainingSampleRow,
)
from app.domain import (
    BudgetBucket,
    Category,
    CategorySpending,
    ConfirmedReceipt,
    MerchantSpending,
    Money,
    ReceiptItem,
    SpendingSummary,
)
from app.ports import (
    ReceiptConfirmationPort,
    ReceiptDraftAlreadyConfirmedError,
    ReceiptDraftNotFoundError,
    ReceiptRepositoryPort,
    TrainingSample,
)


class SQLAlchemyReceiptRepository(
    ReceiptRepositoryPort,
    ReceiptConfirmationPort,
):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save_confirmed_receipt(self, receipt: ConfirmedReceipt) -> None:
        with self.session_factory() as session:
            row = self._receipt_to_row(receipt)
            session.add(row)
            session.commit()

    def confirm_prediction(
        self,
        *,
        user_id: UUID,
        receipt_draft_id: UUID,
        receipt: ConfirmedReceipt,
        target_payload: dict[str, Any],
    ) -> TrainingSample:
        if receipt.user_id != user_id:
            raise ValueError(
                "Receipt user must match confirmation user"
            )

        with self.session_factory() as session:
            with session.begin():
                statement = (
                    select(ReceiptPredictionRow)
                    .where(
                        ReceiptPredictionRow.user_id == user_id,
                        ReceiptPredictionRow.receipt_draft_id
                        == receipt_draft_id,
                    )
                    .with_for_update()
                )

                prediction_row = session.scalar(statement)

                if prediction_row is None:
                    raise ReceiptDraftNotFoundError(
                        "Receipt draft was not found"
                    )

                if prediction_row.confirmed_receipt_id is not None:
                    raise ReceiptDraftAlreadyConfirmedError(
                        "Receipt draft has already been confirmed"
                    )

                training_sample = TrainingSample(
                    user_id=user_id,
                    source_prediction_id=prediction_row.id,
                    input_payload={
                        "image_ref": prediction_row.image_ref,
                        "extractor_name":
                            prediction_row.extractor_name,
                        "model_output":
                            prediction_row.model_output,
                    },
                    target_payload=target_payload,
                )

                session.add(self._receipt_to_row(receipt))
                session.flush()

                session.add(
                    TrainingSampleRow(
                        id=training_sample.id,
                        user_id=training_sample.user_id,
                        source_prediction_id=(
                            training_sample.source_prediction_id
                        ),
                        input_payload=(
                            training_sample.input_payload
                        ),
                        target_payload=(
                            training_sample.target_payload
                        ),
                        is_sanitized=(
                            training_sample.is_sanitized
                        ),
                        created_at=training_sample.created_at,
                    )
                )

                prediction_row.confirmed_receipt_id = receipt.id
                prediction_row.confirmed_at = datetime.now(UTC)

        return training_sample

    def list_receipts(self, user_id: UUID) -> list[ConfirmedReceipt]:
        with self.session_factory() as session:
            statement = (
                select(ReceiptRow)
                .where(ReceiptRow.user_id == user_id)
                .options(selectinload(ReceiptRow.items))
                .order_by(ReceiptRow.confirmed_at.desc())
            )

            rows = session.scalars(statement).all()

            return [self._row_to_receipt(row) for row in rows]

    def get_spending_summary(
        self,
        user_id: UUID,
        from_date: date,
        to_date: date,
    ) -> SpendingSummary:
        receipts = self.list_receipts(user_id=user_id)

        filtered_receipts = [
            receipt
            for receipt in receipts
            if from_date <= self._receipt_date(receipt) <= to_date
        ]

        total_spent = Money.zero()

        category_totals: dict[Category, Decimal] = defaultdict(lambda: Decimal("0.00"))
        category_counts: dict[Category, int] = defaultdict(int)

        merchant_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        merchant_counts: dict[str, int] = defaultdict(int)

        for receipt in filtered_receipts:
            total_spent = total_spent + receipt.total

            merchant_name = receipt.merchant_name or "Unknown merchant"
            merchant_totals[merchant_name] += receipt.total.amount
            merchant_counts[merchant_name] += 1

            for item in receipt.items:
                category_totals[item.category] += item.total_price.amount
                category_counts[item.category] += 1

        by_category = [
            CategorySpending(
                category=category,
                total=Money(amount=amount),
                transaction_count=category_counts[category],
            )
            for category, amount in category_totals.items()
        ]

        by_merchant = [
            MerchantSpending(
                merchant_name=merchant_name,
                total=Money(amount=amount),
                transaction_count=merchant_counts[merchant_name],
            )
            for merchant_name, amount in merchant_totals.items()
        ]

        return SpendingSummary(
            from_date=from_date,
            to_date=to_date,
            total_spent=total_spent,
            by_category=by_category,
            by_merchant=by_merchant,
        )

    def _receipt_to_row(self, receipt: ConfirmedReceipt) -> ReceiptRow:
        return ReceiptRow(
            id=receipt.id,
            user_id=receipt.user_id,
            merchant_name=receipt.merchant_name,
            purchased_at=receipt.purchased_at,
            subtotal_amount=(
                receipt.subtotal.amount
                if receipt.subtotal is not None
                else None
            ),
            subtotal_currency=(
                receipt.subtotal.currency
                if receipt.subtotal is not None
                else None
            ),
            tax_amount=(
                receipt.tax.amount
                if receipt.tax is not None
                else None
            ),
            tax_currency=(
                receipt.tax.currency
                if receipt.tax is not None
                else None
            ),
            total_amount=receipt.total.amount,
            total_currency=receipt.total.currency,
            image_ref=receipt.image_ref,
            confirmed_at=receipt.confirmed_at,
            items=[
                ReceiptItemRow(
                    name=item.name,
                    total_price_amount=item.total_price.amount,
                    total_price_currency=item.total_price.currency,
                    category=item.category.value,
                    bucket=item.bucket.value,
                    quantity=item.quantity,
                    unit_price_amount=item.unit_price.amount if item.unit_price else None,
                    unit_price_currency=item.unit_price.currency if item.unit_price else None,
                    confidence=item.confidence,
                )
                for item in receipt.items
            ],
        )

    def _row_to_receipt(self, row: ReceiptRow) -> ConfirmedReceipt:
        return ConfirmedReceipt(
            id=row.id,
            user_id=row.user_id,
            merchant_name=row.merchant_name,
            purchased_at=row.purchased_at,
            items=[
                self._row_to_item(item_row)
                for item_row in row.items
            ],
            total=Money(
                amount=row.total_amount,
                currency=row.total_currency,
            ),
            subtotal=(
                Money(
                    amount=row.subtotal_amount,
                    currency=(
                        row.subtotal_currency
                        or row.total_currency
                    ),
                )
                if row.subtotal_amount is not None
                else None
            ),
            tax=(
                Money(
                    amount=row.tax_amount,
                    currency=row.tax_currency or row.total_currency,
                )
                if row.tax_amount is not None
                else None
            ),
            image_ref=row.image_ref,
            confirmed_at=row.confirmed_at,
        )

    def _row_to_item(self, row: ReceiptItemRow) -> ReceiptItem:
        unit_price = None
        if row.unit_price_amount is not None:
            unit_price = Money(
                amount=row.unit_price_amount,
                currency=row.unit_price_currency or row.total_price_currency,
            )

        return ReceiptItem(
            name=row.name,
            total_price=Money(
                amount=row.total_price_amount,
                currency=row.total_price_currency,
            ),
            category=self._parse_category(row.category),
            bucket=self._parse_bucket(row.bucket),
            quantity=row.quantity,
            unit_price=unit_price,
            confidence=row.confidence,
        )

    def _parse_category(self, value: str) -> Category:
        try:
            return Category(value)
        except ValueError:
            return Category.UNKNOWN

    def _parse_bucket(self, value: str) -> BudgetBucket:
        try:
            return BudgetBucket(value)
        except ValueError:
            return BudgetBucket.UNKNOWN

    def _receipt_date(self, receipt: ConfirmedReceipt) -> date:
        source_datetime = receipt.purchased_at or receipt.confirmed_at
        return source_datetime.date()
