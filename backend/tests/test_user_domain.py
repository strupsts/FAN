from __future__ import annotations

import unittest
from datetime import datetime
from uuid import uuid4

from app.domain import User, UserPreferences


class UserDomainTests(unittest.TestCase):
    def test_preferences_normalize_country_and_currencies(
        self,
    ) -> None:
        preferences = UserPreferences(
            user_id=uuid4(),
            interface_language=" en ",
            formatting_locale=" en-CA ",
            home_country=" ca ",
            default_receipt_currency=" cad ",
            reporting_currency=" usd ",
            time_zone=" America/Edmonton ",
        )

        self.assertEqual(
            preferences.interface_language,
            "en",
        )
        self.assertEqual(
            preferences.formatting_locale,
            "en-CA",
        )
        self.assertEqual(
            preferences.home_country,
            "CA",
        )
        self.assertEqual(
            preferences.default_receipt_currency,
            "CAD",
        )
        self.assertEqual(
            preferences.reporting_currency,
            "USD",
        )
        self.assertEqual(
            preferences.time_zone,
            "America/Edmonton",
        )
        self.assertFalse(
            preferences.onboarding_completed
        )

    def test_preferences_reject_invalid_currency(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "three-letter currency code",
        ):
            UserPreferences(
                user_id=uuid4(),
                interface_language="en",
                formatting_locale="en-CA",
                home_country="CA",
                default_receipt_currency="dollars",
                reporting_currency="CAD",
                time_zone="America/Edmonton",
            )

    def test_preferences_reject_invalid_country(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "two-letter country code",
        ):
            UserPreferences(
                user_id=uuid4(),
                interface_language="en",
                formatting_locale="en-CA",
                home_country="Canada",
                default_receipt_currency="CAD",
                reporting_currency="CAD",
                time_zone="America/Edmonton",
            )

    def test_preferences_reject_non_ascii_currency(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "three-letter currency code",
        ):
            UserPreferences(
                user_id=uuid4(),
                interface_language="ru",
                formatting_locale="ru-RU",
                home_country="RU",
                default_receipt_currency="руб",
                reporting_currency="CAD",
                time_zone="Europe/Moscow",
            )

    def test_preferences_reject_non_ascii_country(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "two-letter country code",
        ):
            UserPreferences(
                user_id=uuid4(),
                interface_language="ru",
                formatting_locale="ru-RU",
                home_country="РФ",
                default_receipt_currency="RUB",
                reporting_currency="CAD",
                time_zone="Europe/Moscow",
            )

    def test_user_rejects_naive_created_at(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "created_at must be timezone-aware",
        ):
            User(
                id=uuid4(),
                created_at=datetime(2026, 7, 29, 12, 0),
            )


if __name__ == "__main__":
    unittest.main()
