from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.outbound.db.sqlalchemy_models import Base
from app.adapters.outbound.db.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.infrastructure.container import build_container


class UserRepositoryWiringTests(unittest.TestCase):
    def test_container_builds_user_repository(self) -> None:
        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={
                "check_same_thread": False,
            },
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)

        session_factory = sessionmaker[Session](
            bind=engine,
            expire_on_commit=False,
        )

        try:
            with (
                patch(
                    "app.infrastructure.container."
                    "create_db_engine",
                    return_value=engine,
                ),
                patch(
                    "app.infrastructure.container."
                    "create_session_factory",
                    return_value=session_factory,
                ),
            ):
                container = build_container()

            self.assertIsInstance(
                container.user_repository,
                SQLAlchemyUserRepository,
            )
            self.assertIs(
                container.user_repository.session_factory,
                session_factory,
            )
            self.assertIs(
                container
                .get_current_user_profile_use_case
                .user_repository,
                container.user_repository,
            )
            self.assertIs(
                container
                .set_user_preferences_use_case
                .user_repository,
                container.user_repository,
            )
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
