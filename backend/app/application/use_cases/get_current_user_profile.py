from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.application.errors import CurrentUserNotFoundError
from app.domain import User, UserPreferences
from app.ports import UserRepositoryPort


@dataclass(frozen=True)
class CurrentUserProfile:
    user: User
    preferences: UserPreferences | None


class GetCurrentUserProfileUseCase:
    def __init__(
        self,
        user_repository: UserRepositoryPort,
    ) -> None:
        self.user_repository = user_repository

    def execute(
        self,
        user_id: UUID,
    ) -> CurrentUserProfile:
        user = self.user_repository.get_user(user_id)

        if user is None:
            raise CurrentUserNotFoundError(
                f"Current user {user_id} was not found"
            )

        preferences = self.user_repository.get_preferences(
            user_id
        )

        return CurrentUserProfile(
            user=user,
            preferences=preferences,
        )
