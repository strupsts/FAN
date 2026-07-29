from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain import User, UserPreferences


class UserNotFoundError(LookupError):
    """Raised when an operation requires a missing user."""


class UserRepositoryPort(Protocol):
    def get_user(
        self,
        user_id: UUID,
    ) -> User | None:
        """Return a user or None when it does not exist."""
        ...

    def get_preferences(
        self,
        user_id: UUID,
    ) -> UserPreferences | None:
        """Return regional preferences or None."""
        ...

    def save_preferences(
        self,
        preferences: UserPreferences,
    ) -> None:
        """Create or update preferences for an existing user."""
        ...
