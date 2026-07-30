from __future__ import annotations

from uuid import UUID

from app.infrastructure import (
    AppContainer,
    build_container,
    get_settings,
)


_container = build_container()

# Temporary current-user implementation until authentication exists.
_FAKE_USER_ID = get_settings().dev_user_id


def get_container() -> AppContainer:
    return _container


def get_current_user_id() -> UUID:
    return _FAKE_USER_ID
