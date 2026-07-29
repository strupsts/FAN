from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.db.sqlalchemy_models import (
    UserPreferencesRow,
    UserRow,
)
from app.domain import User, UserPreferences
from app.ports import (
    UserNotFoundError,
    UserRepositoryPort,
)


class SQLAlchemyUserRepository(UserRepositoryPort):
    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.session_factory = session_factory

    def get_user(
        self,
        user_id: UUID,
    ) -> User | None:
        with self.session_factory() as session:
            row = session.get(UserRow, user_id)

            if row is None:
                return None

            return self._row_to_user(row)

    def get_preferences(
        self,
        user_id: UUID,
    ) -> UserPreferences | None:
        with self.session_factory() as session:
            row = session.get(
                UserPreferencesRow,
                user_id,
            )

            if row is None:
                return None

            return self._row_to_preferences(row)

    def save_preferences(
        self,
        preferences: UserPreferences,
    ) -> None:
        with self.session_factory() as session:
            user_row = session.get(
                UserRow,
                preferences.user_id,
            )

            if user_row is None:
                raise UserNotFoundError(
                    f"User {preferences.user_id} was not found"
                )

            row = session.get(
                UserPreferencesRow,
                preferences.user_id,
            )

            if row is None:
                session.add(
                    self._preferences_to_row(preferences)
                )
            else:
                self._update_preferences_row(
                    row=row,
                    preferences=preferences,
                )

            session.commit()

    def _row_to_user(
        self,
        row: UserRow,
    ) -> User:
        return User(
            id=row.id,
            created_at=self._as_aware_utc(
                row.created_at
            ),
        )

    def _row_to_preferences(
        self,
        row: UserPreferencesRow,
    ) -> UserPreferences:
        return UserPreferences(
            user_id=row.user_id,
            interface_language=row.interface_language,
            formatting_locale=row.formatting_locale,
            home_country=row.home_country,
            default_receipt_currency=(
                row.default_receipt_currency
            ),
            reporting_currency=row.reporting_currency,
            time_zone=row.time_zone,
            onboarding_completed=(
                row.onboarding_completed
            ),
            updated_at=self._as_aware_utc(
                row.updated_at
            ),
        )

    def _preferences_to_row(
        self,
        preferences: UserPreferences,
    ) -> UserPreferencesRow:
        return UserPreferencesRow(
            user_id=preferences.user_id,
            interface_language=(
                preferences.interface_language
            ),
            formatting_locale=(
                preferences.formatting_locale
            ),
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

    def _update_preferences_row(
        self,
        *,
        row: UserPreferencesRow,
        preferences: UserPreferences,
    ) -> None:
        row.interface_language = (
            preferences.interface_language
        )
        row.formatting_locale = (
            preferences.formatting_locale
        )
        row.home_country = preferences.home_country
        row.default_receipt_currency = (
            preferences.default_receipt_currency
        )
        row.reporting_currency = (
            preferences.reporting_currency
        )
        row.time_zone = preferences.time_zone
        row.onboarding_completed = (
            preferences.onboarding_completed
        )
        row.updated_at = preferences.updated_at

    def _as_aware_utc(
        self,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)
