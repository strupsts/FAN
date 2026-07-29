from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.outbound.db.sqlalchemy_models import (
    Base,
    UserPreferencesRow,
    UserRow,
)
from app.adapters.outbound.db.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.domain import UserPreferences
from app.ports import UserNotFoundError


class SQLAlchemyUserRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={
                "check_same_thread": False,
            },
            poolclass=StaticPool,
        )

        Base.metadata.create_all(self.engine)

        self.session_factory = sessionmaker[Session](
            bind=self.engine,
            expire_on_commit=False,
        )
        self.repository = SQLAlchemyUserRepository(
            session_factory=self.session_factory,
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_get_user_and_preferences(self) -> None:
        user_id = uuid4()
        created_at = datetime(
            2026,
            7,
            29,
            22,
            0,
            tzinfo=UTC,
        )
        updated_at = datetime(
            2026,
            7,
            29,
            22,
            5,
            tzinfo=UTC,
        )

        self._insert_user(
            user_id=user_id,
            created_at=created_at,
        )
        self._insert_preferences(
            UserPreferences(
                user_id=user_id,
                interface_language="en",
                formatting_locale="en-CA",
                home_country="CA",
                default_receipt_currency="CAD",
                reporting_currency="USD",
                time_zone="America/Edmonton",
                onboarding_completed=True,
                updated_at=updated_at,
            )
        )

        user = self.repository.get_user(user_id)
        preferences = self.repository.get_preferences(
            user_id
        )

        self.assertIsNotNone(user)
        self.assertIsNotNone(preferences)

        assert user is not None
        assert preferences is not None

        self.assertEqual(user.id, user_id)
        self.assertEqual(
            user.created_at,
            created_at,
        )
        self.assertEqual(
            preferences.reporting_currency,
            "USD",
        )
        self.assertTrue(
            preferences.onboarding_completed
        )
        self.assertEqual(
            preferences.updated_at,
            updated_at,
        )

    def test_missing_user_and_preferences_return_none(
        self,
    ) -> None:
        user_id = uuid4()

        self.assertIsNone(
            self.repository.get_user(user_id)
        )
        self.assertIsNone(
            self.repository.get_preferences(user_id)
        )

    def test_save_preferences_creates_and_updates(
        self,
    ) -> None:
        user_id = uuid4()
        self._insert_user(user_id=user_id)

        original = UserPreferences(
            user_id=user_id,
            interface_language="en",
            formatting_locale="en-CA",
            home_country="CA",
            default_receipt_currency="CAD",
            reporting_currency="CAD",
            time_zone="America/Edmonton",
        )

        self.repository.save_preferences(original)

        created = self.repository.get_preferences(
            user_id
        )

        self.assertIsNotNone(created)
        assert created is not None

        self.assertEqual(
            created.interface_language,
            "en",
        )
        self.assertEqual(
            created.reporting_currency,
            "CAD",
        )

        updated = UserPreferences(
            user_id=user_id,
            interface_language="ru",
            formatting_locale="ru-RU",
            home_country="CA",
            default_receipt_currency="CAD",
            reporting_currency="EUR",
            time_zone="America/Edmonton",
            onboarding_completed=True,
            updated_at=datetime(
                2026,
                7,
                30,
                1,
                0,
                tzinfo=UTC,
            ),
        )

        self.repository.save_preferences(updated)

        saved = self.repository.get_preferences(
            user_id
        )

        self.assertIsNotNone(saved)
        assert saved is not None

        self.assertEqual(
            saved.interface_language,
            "ru",
        )
        self.assertEqual(
            saved.formatting_locale,
            "ru-RU",
        )
        self.assertEqual(
            saved.reporting_currency,
            "EUR",
        )
        self.assertTrue(
            saved.onboarding_completed
        )

    def test_save_preferences_rejects_missing_user(
        self,
    ) -> None:
        preferences = UserPreferences(
            user_id=uuid4(),
            interface_language="en",
            formatting_locale="en-CA",
            home_country="CA",
            default_receipt_currency="CAD",
            reporting_currency="CAD",
            time_zone="America/Edmonton",
        )

        with self.assertRaises(UserNotFoundError):
            self.repository.save_preferences(
                preferences
            )

    def test_updating_one_user_does_not_change_another(
        self,
    ) -> None:
        first_user_id = uuid4()
        second_user_id = uuid4()

        self._insert_user(first_user_id)
        self._insert_user(second_user_id)

        self.repository.save_preferences(
            UserPreferences(
                user_id=first_user_id,
                interface_language="en",
                formatting_locale="en-CA",
                home_country="CA",
                default_receipt_currency="CAD",
                reporting_currency="CAD",
                time_zone="America/Edmonton",
            )
        )
        self.repository.save_preferences(
            UserPreferences(
                user_id=second_user_id,
                interface_language="ru",
                formatting_locale="ru-RU",
                home_country="UA",
                default_receipt_currency="UAH",
                reporting_currency="EUR",
                time_zone="Europe/Kyiv",
            )
        )

        self.repository.save_preferences(
            UserPreferences(
                user_id=first_user_id,
                interface_language="en",
                formatting_locale="en-US",
                home_country="US",
                default_receipt_currency="USD",
                reporting_currency="USD",
                time_zone="America/Los_Angeles",
            )
        )

        second = self.repository.get_preferences(
            second_user_id
        )

        self.assertIsNotNone(second)
        assert second is not None

        self.assertEqual(
            second.home_country,
            "UA",
        )
        self.assertEqual(
            second.default_receipt_currency,
            "UAH",
        )
        self.assertEqual(
            second.reporting_currency,
            "EUR",
        )

    def _insert_user(
        self,
        user_id: UUID,
        created_at: datetime | None = None,
    ) -> None:
        with self.session_factory() as session:
            session.add(
                UserRow(
                    id=user_id,
                    created_at=created_at
                    or datetime.now(UTC),
                )
            )
            session.commit()

    def _insert_preferences(
        self,
        preferences: UserPreferences,
    ) -> None:
        with self.session_factory() as session:
            session.add(
                UserPreferencesRow(
                    user_id=preferences.user_id,
                    interface_language=(
                        preferences.interface_language
                    ),
                    formatting_locale=(
                        preferences.formatting_locale
                    ),
                    home_country=(
                        preferences.home_country
                    ),
                    default_receipt_currency=(
                        preferences
                        .default_receipt_currency
                    ),
                    reporting_currency=(
                        preferences.reporting_currency
                    ),
                    time_zone=preferences.time_zone,
                    onboarding_completed=(
                        preferences
                        .onboarding_completed
                    ),
                    updated_at=preferences.updated_at,
                )
            )
            session.commit()


if __name__ == "__main__":
    unittest.main()
