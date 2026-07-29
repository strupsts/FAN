from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
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


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    preferences: Mapped[UserPreferencesRow | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )


class UserPreferencesRow(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_user_preferences_user",
        ),
        primary_key=True,
    )

    interface_language: Mapped[str] = mapped_column(
        String(35),
        nullable=False,
    )
    formatting_locale: Mapped[str] = mapped_column(
        String(35),
        nullable=False,
    )
    home_country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )
    default_receipt_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    reporting_currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    time_zone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    user: Mapped[UserRow] = relationship(
        back_populates="preferences",
    )


class ReceiptRow(Base):
    __tablename__ = "receipts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_receipts_user",
        ),
        index=True,
    )
    merchant_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    purchased_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False),
        nullable=True,
    )

    subtotal_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    subtotal_currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )
    tax_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    tax_currency: Mapped[str | None] = mapped_column(
        String(3),
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
        UniqueConstraint(
            "confirmed_receipt_id",
            name="uq_receipt_predictions_confirmed_receipt",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_receipt_predictions_user",
        ),
        index=True,
    )
    receipt_draft_id: Mapped[UUID] = mapped_column(index=True)

    image_ref: Mapped[str] = mapped_column(String(1000))
    extractor_name: Mapped[str] = mapped_column(String(255))

    confirmed_receipt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "receipts.id",
            ondelete="RESTRICT",
            name="fk_receipt_predictions_confirmed_receipt",
        ),
        nullable=True,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    model_output: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )



class TrainingSampleRow(Base):
    __tablename__ = "training_samples"
    __table_args__ = (
        UniqueConstraint(
            "source_prediction_id",
            name="uq_training_samples_source_prediction",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
            name="fk_training_samples_user",
        ),
        index=True,
    )
    source_prediction_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "receipt_predictions.id",
            ondelete="CASCADE",
            name="fk_training_samples_source_prediction",
        ),
        nullable=False,
    )

    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    target_payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    is_sanitized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )
