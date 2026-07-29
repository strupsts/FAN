from __future__ import annotations

import unittest

from app.adapters.outbound.db.sqlalchemy_models import Base


class UserPersistenceModelTests(unittest.TestCase):
    def test_user_tables_are_registered(self) -> None:
        self.assertIn(
            "users",
            Base.metadata.tables,
        )
        self.assertIn(
            "user_preferences",
            Base.metadata.tables,
        )

    def test_preferences_have_one_to_one_user_fk(
        self,
    ) -> None:
        preferences = Base.metadata.tables[
            "user_preferences"
        ]
        user_id = preferences.c.user_id

        self.assertTrue(user_id.primary_key)

        foreign_keys = list(user_id.foreign_keys)

        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(
            foreign_keys[0].target_fullname,
            "users.id",
        )
        self.assertEqual(
            foreign_keys[0].ondelete,
            "CASCADE",
        )

        self.assertEqual(
            preferences
            .c.default_receipt_currency
            .type.length,
            3,
        )
        self.assertEqual(
            preferences.c.reporting_currency.type.length,
            3,
        )

        self.assertIsNone(
            preferences
            .c.default_receipt_currency
            .default
        )
        self.assertIsNone(
            preferences.c.reporting_currency.default
        )

    def test_user_owned_tables_reference_users(
        self,
    ) -> None:
        table_names = [
            "receipts",
            "receipt_predictions",
            "training_samples",
        ]

        for table_name in table_names:
            with self.subTest(table=table_name):
                table = Base.metadata.tables[table_name]
                foreign_keys = list(
                    table.c.user_id.foreign_keys
                )

                self.assertEqual(
                    len(foreign_keys),
                    1,
                )
                self.assertEqual(
                    foreign_keys[0].target_fullname,
                    "users.id",
                )
                self.assertEqual(
                    foreign_keys[0].ondelete,
                    "CASCADE",
                )


if __name__ == "__main__":
    unittest.main()
