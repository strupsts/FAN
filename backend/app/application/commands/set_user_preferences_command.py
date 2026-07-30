from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SetUserPreferencesCommand:
    user_id: UUID
    interface_language: str
    formatting_locale: str
    home_country: str
    default_receipt_currency: str
    reporting_currency: str
    time_zone: str
    onboarding_completed: bool
