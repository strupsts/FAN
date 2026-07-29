from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


def _normalize_required_string(
    value: str,
    field_name: str,
) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty")

    return normalized


def _normalize_currency(
    value: str,
    field_name: str,
) -> str:
    normalized = _normalize_required_string(
        value,
        field_name,
    ).upper()

    if (
        len(normalized) != 3
        or not normalized.isascii()
        or not normalized.isalpha()
    ):
        raise ValueError(
            f"{field_name} must be a three-letter currency code"
        )

    return normalized


def _normalize_country(value: str) -> str:
    normalized = _normalize_required_string(
        value,
        "home_country",
    ).upper()

    if (
        len(normalized) != 2
        or not normalized.isascii()
        or not normalized.isalpha()
    ):
        raise ValueError(
            "home_country must be a two-letter country code"
        )

    return normalized


def _ensure_timezone_aware(
    value: datetime,
    field_name: str,
) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(
            f"{field_name} must be timezone-aware"
        )


@dataclass(frozen=True)
class User:
    id: UUID
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        _ensure_timezone_aware(
            self.created_at,
            "created_at",
        )


@dataclass(frozen=True)
class UserPreferences:
    user_id: UUID

    interface_language: str
    formatting_locale: str
    home_country: str
    default_receipt_currency: str
    reporting_currency: str
    time_zone: str

    onboarding_completed: bool = False
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "interface_language",
            _normalize_required_string(
                self.interface_language,
                "interface_language",
            ),
        )
        object.__setattr__(
            self,
            "formatting_locale",
            _normalize_required_string(
                self.formatting_locale,
                "formatting_locale",
            ),
        )
        object.__setattr__(
            self,
            "home_country",
            _normalize_country(self.home_country),
        )
        object.__setattr__(
            self,
            "default_receipt_currency",
            _normalize_currency(
                self.default_receipt_currency,
                "default_receipt_currency",
            ),
        )
        object.__setattr__(
            self,
            "reporting_currency",
            _normalize_currency(
                self.reporting_currency,
                "reporting_currency",
            ),
        )
        object.__setattr__(
            self,
            "time_zone",
            _normalize_required_string(
                self.time_zone,
                "time_zone",
            ),
        )

        _ensure_timezone_aware(
            self.updated_at,
            "updated_at",
        )
