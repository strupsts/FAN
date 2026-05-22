from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.domain.category import Category
from app.domain.money import Money


@dataclass(frozen=True)
class CategorySpending:
    category: Category
    total: Money
    transaction_count: int

    def __post_init__(self) -> None:
        if self.transaction_count < 0:
            raise ValueError("transaction_count cannot be negative")


@dataclass(frozen=True)
class MerchantSpending:
    merchant_name: str
    total: Money
    transaction_count: int

    def __post_init__(self) -> None:
        if not self.merchant_name.strip():
            raise ValueError("merchant_name must not be empty")

        if self.transaction_count < 0:
            raise ValueError("transaction_count cannot be negative")


@dataclass(frozen=True)
class SpendingSummary:
    from_date: date
    to_date: date
    total_spent: Money
    by_category: list[CategorySpending] = field(default_factory=list)
    by_merchant: list[MerchantSpending] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.from_date > self.to_date:
            raise ValueError("from_date cannot be after to_date")
