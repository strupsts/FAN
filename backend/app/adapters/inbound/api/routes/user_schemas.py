from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.application import CurrentUserProfile
from app.domain import UserPreferences


class SetUserPreferencesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interface_language: str = Field(min_length=1)
    formatting_locale: str = Field(min_length=1)

    home_country: str = Field(
        min_length=2,
        max_length=2,
        pattern=r"^[A-Za-z]{2}$",
    )
    default_receipt_currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    )
    reporting_currency: str = Field(
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    )

    time_zone: str = Field(min_length=1)
    onboarding_completed: bool


class UserPreferencesResponse(BaseModel):
    user_id: UUID
    interface_language: str
    formatting_locale: str
    home_country: str
    default_receipt_currency: str
    reporting_currency: str
    time_zone: str
    onboarding_completed: bool
    updated_at: datetime


class CurrentUserProfileResponse(BaseModel):
    id: UUID
    created_at: datetime
    preferences: UserPreferencesResponse | None


def preferences_to_response(
    preferences: UserPreferences,
) -> UserPreferencesResponse:
    return UserPreferencesResponse(
        user_id=preferences.user_id,
        interface_language=(
            preferences.interface_language
        ),
        formatting_locale=preferences.formatting_locale,
        home_country=preferences.home_country,
        default_receipt_currency=(
            preferences.default_receipt_currency
        ),
        reporting_currency=(
            preferences.reporting_currency
        ),
        time_zone=preferences.time_zone,
        onboarding_completed=(
            preferences.onboarding_completed
        ),
        updated_at=preferences.updated_at,
    )


def profile_to_response(
    profile: CurrentUserProfile,
) -> CurrentUserProfileResponse:
    return CurrentUserProfileResponse(
        id=profile.user.id,
        created_at=profile.user.created_at,
        preferences=(
            preferences_to_response(profile.preferences)
            if profile.preferences is not None
            else None
        ),
    )
