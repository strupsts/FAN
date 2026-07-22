from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


class ReceiptRow(Base):
    __tablename__ = "receipts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(index=True)
    merchant_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    purchased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total_currency: Mapped[str] = mapped_column(
        String(3),
        default="CAD",
    )
    image_ref: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False)
    )

    items: Mapped[list[ReceiptItemRow]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )


class ReceiptItemRow(Base):
    __tablename__ = "receipt_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"),
        index=True,
    )

    name: Mapped[str] = mapped_column(String(500))
    total_price_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2)
    )
    total_price_currency: Mapped[str] = mapped_column(
        String(3),
        default="CAD",
    )

    category: Mapped[str] = mapped_column(
        String(100),
        default="unknown",
    )
    bucket: Mapped[str] = mapped_column(
        String(100),
        default="unknown",
    )

    quantity: Mapped[float | None] = mapped_column(nullable=True)
    unit_price_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    unit_price_currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(nullable=True)

    receipt: Mapped[ReceiptRow] = relationship(
        back_populates="items"
    )


class ReceiptPredictionRow(Base):
    __tablename__ = "receipt_predictions"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "receipt_draft_id",
            name="uq_receipt_predictions_user_draft",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(index=True)
    receipt_draft_id: Mapped[UUID] = mapped_column(index=True)

    image_ref: Mapped[str] = mapped_column(String(1000))
    extractor_name: Mapped[str] = mapped_column(String(255))

    model_output: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
