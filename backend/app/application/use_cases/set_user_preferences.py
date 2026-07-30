from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.application.commands.set_user_preferences_command import (
    SetUserPreferencesCommand,
)
from app.application.errors import CurrentUserNotFoundError
from app.domain import UserPreferences
from app.ports import (
    UserNotFoundError,
    UserRepositoryPort,
)


class SetUserPreferencesUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.user_repository = user_repository
        self.clock = clock or (
            lambda: datetime.now(UTC)
        )

    def execute(
        self,
        command: SetUserPreferencesCommand,
    ) -> UserPreferences:
        preferences = UserPreferences(
            user_id=command.user_id,
            interface_language=(
                command.interface_language
            ),
            formatting_locale=(
                command.formatting_locale
            ),
            home_country=command.home_country,
            default_receipt_currency=(
                command.default_receipt_currency
            ),
            reporting_currency=(
                command.reporting_currency
            ),
            time_zone=command.time_zone,
            onboarding_completed=(
                command.onboarding_completed
            ),
            updated_at=self.clock(),
        )

        try:
            self.user_repository.save_preferences(
                preferences
            )
        except UserNotFoundError as error:
            raise CurrentUserNotFoundError(
                f"Current user {command.user_id} "
                "was not found"
            ) from error

        return preferences
