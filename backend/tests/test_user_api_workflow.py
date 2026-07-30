from __future__ import annotations

import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.inbound.api.dependencies import (
    get_container,
    get_current_user_id,
)
from app.adapters.outbound.db.sqlalchemy_models import (
    Base,
    UserRow,
)
from app.adapters.outbound.db.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.application import (
    GetCurrentUserProfileUseCase,
    SetUserPreferencesUseCase,
)
from app.domain import UserPreferences
from app.main import create_app


class UserAPIWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.first_user_id = uuid4()
        self.second_user_id = uuid4()
        self.current_user_id = self.first_user_id

        self.engine = create_engine(
            "sqlite+pysqlite://",
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

        with self.session_factory() as session:
            session.add_all(
                [
                    UserRow(id=self.first_user_id),
                    UserRow(id=self.second_user_id),
                ]
            )
            session.commit()

        self.repository = SQLAlchemyUserRepository(
            session_factory=self.session_factory,
        )

        container = SimpleNamespace(
            get_current_user_profile_use_case=(
                GetCurrentUserProfileUseCase(
                    user_repository=self.repository,
                )
            ),
            set_user_preferences_use_case=(
                SetUserPreferencesUseCase(
                    user_repository=self.repository,
                )
            ),
        )

        self.app = create_app()
        self.app.dependency_overrides[
            get_container
        ] = lambda: container
        self.app.dependency_overrides[
            get_current_user_id
        ] = lambda: self.current_user_id

        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.app.dependency_overrides.clear()
        self.engine.dispose()

    def test_get_current_user_without_preferences(
        self,
    ) -> None:
        response = self.client.get("/api/users/me")

        self.assertEqual(response.status_code, 200)

        body = response.json()

        self.assertEqual(
            body["id"],
            str(self.first_user_id),
        )
        self.assertIsNone(body["preferences"])

    def test_put_preferences_then_get_profile(
        self,
    ) -> None:
        put_response = self.client.put(
            "/api/users/me/preferences",
            json=self._payload(),
        )

        self.assertEqual(
            put_response.status_code,
            200,
        )

        preferences = put_response.json()

        self.assertEqual(
            preferences["user_id"],
            str(self.first_user_id),
        )
        self.assertEqual(
            preferences["home_country"],
            "CA",
        )
        self.assertEqual(
            preferences["default_receipt_currency"],
            "CAD",
        )
        self.assertEqual(
            preferences["reporting_currency"],
            "USD",
        )

        get_response = self.client.get(
            "/api/users/me"
        )

        self.assertEqual(
            get_response.status_code,
            200,
        )
        self.assertEqual(
            get_response.json()["preferences"][
                "reporting_currency"
            ],
            "USD",
        )

    def test_request_cannot_supply_user_id(
        self,
    ) -> None:
        payload = self._payload()
        payload["user_id"] = str(
            self.second_user_id
        )

        response = self.client.put(
            "/api/users/me/preferences",
            json=payload,
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(
            self.repository.get_preferences(
                self.first_user_id
            )
        )
        self.assertIsNone(
            self.repository.get_preferences(
                self.second_user_id
            )
        )

    def test_update_is_isolated_to_current_user(
        self,
    ) -> None:
        second_preferences = UserPreferences(
            user_id=self.second_user_id,
            interface_language="en",
            formatting_locale="de-DE",
            home_country="DE",
            default_receipt_currency="EUR",
            reporting_currency="EUR",
            time_zone="Europe/Berlin",
            onboarding_completed=True,
        )
        self.repository.save_preferences(
            second_preferences
        )

        response = self.client.put(
            "/api/users/me/preferences",
            json=self._payload(),
        )

        self.assertEqual(response.status_code, 200)

        unchanged = self.repository.get_preferences(
            self.second_user_id
        )

        self.assertIsNotNone(unchanged)
        self.assertEqual(
            unchanged.reporting_currency,
            "EUR",
        )
        self.assertEqual(
            unchanged.time_zone,
            "Europe/Berlin",
        )

    def test_missing_current_user_returns_404(
        self,
    ) -> None:
        self.current_user_id = uuid4()

        get_response = self.client.get(
            "/api/users/me"
        )
        put_response = self.client.put(
            "/api/users/me/preferences",
            json=self._payload(),
        )

        self.assertEqual(
            get_response.status_code,
            404,
        )
        self.assertEqual(
            put_response.status_code,
            404,
        )

    def test_put_preflight_is_allowed(self) -> None:
        response = self.client.options(
            "/api/users/me/preferences",
            headers={
                "Origin": "http://localhost",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": (
                    "content-type"
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers[
                "access-control-allow-origin"
            ],
            "http://localhost",
        )

    def _payload(self) -> dict:
        return {
            "interface_language": "ru",
            "formatting_locale": "en-CA",
            "home_country": "ca",
            "default_receipt_currency": "cad",
            "reporting_currency": "usd",
            "time_zone": "America/Edmonton",
            "onboarding_completed": True,
        }


if __name__ == "__main__":
    unittest.main()
