from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "CAD"

    def __post_init__(self) -> None:
        try:
            normalized_amount = Decimal(self.amount).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        except (InvalidOperation, ValueError) as error:
            raise ValueError("Money amount must be a valid decimal value") from error

        if not normalized_amount.is_finite():
            raise ValueError("Money amount must be finite")

        if not self.currency:
            raise ValueError("Currency must not be empty")

        object.__setattr__(self, "amount", normalized_amount)
        object.__setattr__(self, "currency", self.currency.upper())

    @classmethod
    def zero(cls, currency: str = "CAD") -> "Money":
        return cls(amount=Decimal("0.00"), currency=currency)

    def __add__(self, other: "Money") -> "Money":
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def _ensure_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError("Cannot operate on money with different currencies")
