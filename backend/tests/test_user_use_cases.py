from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application import (
    CurrentUserNotFoundError,
    GetCurrentUserProfileUseCase,
    SetUserPreferencesCommand,
    SetUserPreferencesUseCase,
)
from app.domain import User, UserPreferences
from app.ports import UserNotFoundError


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}
        self.preferences: dict[
            UUID,
            UserPreferences,
        ] = {}

    def get_user(
        self,
        user_id: UUID,
    ) -> User | None:
        return self.users.get(user_id)

    def get_preferences(
        self,
        user_id: UUID,
    ) -> UserPreferences | None:
        return self.preferences.get(user_id)

    def save_preferences(
        self,
        preferences: UserPreferences,
    ) -> None:
        if preferences.user_id not in self.users:
            raise UserNotFoundError(
                f"User {preferences.user_id} "
                "was not found"
            )

        self.preferences[
            preferences.user_id
        ] = preferences


class UserUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeUserRepository()

    def test_get_profile_returns_user_and_preferences(
        self,
    ) -> None:
        user = User(id=uuid4())
        preferences = self._preferences(
            user_id=user.id,
        )

        self.repository.users[user.id] = user
        self.repository.preferences[
            user.id
        ] = preferences

        use_case = GetCurrentUserProfileUseCase(
            user_repository=self.repository,
        )

        profile = use_case.execute(user.id)

        self.assertEqual(profile.user, user)
        self.assertEqual(
            profile.preferences,
            preferences,
        )

    def test_get_profile_allows_missing_preferences(
        self,
    ) -> None:
        user = User(id=uuid4())
        self.repository.users[user.id] = user

        use_case = GetCurrentUserProfileUseCase(
            user_repository=self.repository,
        )

        profile = use_case.execute(user.id)

        self.assertEqual(profile.user, user)
        self.assertIsNone(profile.preferences)

    def test_get_profile_rejects_missing_user(
        self,
    ) -> None:
        use_case = GetCurrentUserProfileUseCase(
            user_repository=self.repository,
        )

        with self.assertRaises(
            CurrentUserNotFoundError
        ):
            use_case.execute(uuid4())

    def test_set_preferences_creates_normalized_values(
        self,
    ) -> None:
        user = User(id=uuid4())
        self.repository.users[user.id] = user

        updated_at = datetime(
            2026,
            7,
            30,
            0,
            30,
            tzinfo=UTC,
        )

        use_case = SetUserPreferencesUseCase(
            user_repository=self.repository,
            clock=lambda: updated_at,
        )

        saved = use_case.execute(
            SetUserPreferencesCommand(
                user_id=user.id,
                interface_language="ru",
                formatting_locale="en-CA",
                home_country="ca",
                default_receipt_currency="cad",
                reporting_currency="usd",
                time_zone="America/Edmonton",
                onboarding_completed=True,
            )
        )

        self.assertEqual(saved.home_country, "CA")
        self.assertEqual(
            saved.default_receipt_currency,
            "CAD",
        )
        self.assertEqual(
            saved.reporting_currency,
            "USD",
        )
        self.assertEqual(
            saved.updated_at,
            updated_at,
        )
        self.assertEqual(
            self.repository.preferences[user.id],
            saved,
        )

    def test_set_preferences_updates_only_target_user(
        self,
    ) -> None:
        first_user = User(id=uuid4())
        second_user = User(id=uuid4())

        self.repository.users[
            first_user.id
        ] = first_user
        self.repository.users[
            second_user.id
        ] = second_user

        second_preferences = self._preferences(
            user_id=second_user.id,
            reporting_currency="EUR",
        )
        self.repository.preferences[
            second_user.id
        ] = second_preferences

        use_case = SetUserPreferencesUseCase(
            user_repository=self.repository,
        )

        use_case.execute(
            SetUserPreferencesCommand(
                user_id=first_user.id,
                interface_language="en",
                formatting_locale="en-US",
                home_country="US",
                default_receipt_currency="USD",
                reporting_currency="USD",
                time_zone="America/Los_Angeles",
                onboarding_completed=False,
            )
        )

        self.assertEqual(
            self.repository.preferences[
                second_user.id
            ],
            second_preferences,
        )

    def test_set_preferences_rejects_missing_user(
        self,
    ) -> None:
        use_case = SetUserPreferencesUseCase(
            user_repository=self.repository,
        )

        command = SetUserPreferencesCommand(
            user_id=uuid4(),
            interface_language="en",
            formatting_locale="en-CA",
            home_country="CA",
            default_receipt_currency="CAD",
            reporting_currency="CAD",
            time_zone="America/Edmonton",
            onboarding_completed=False,
        )

        with self.assertRaises(
            CurrentUserNotFoundError
        ):
            use_case.execute(command)

    def _preferences(
        self,
        *,
        user_id: UUID,
        reporting_currency: str = "CAD",
    ) -> UserPreferences:
        return UserPreferences(
            user_id=user_id,
            interface_language="en",
            formatting_locale="en-CA",
            home_country="CA",
            default_receipt_currency="CAD",
            reporting_currency=reporting_currency,
            time_zone="America/Edmonton",
            onboarding_completed=False,
        )


if __name__ == "__main__":
    unittest.main()
