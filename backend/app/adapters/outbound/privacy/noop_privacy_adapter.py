from __future__ import annotations

from app.ports import PrivacyRedactorPort


class NoopPrivacyAdapter(PrivacyRedactorPort):
    def redact_text(self, text: str) -> str:
        return text

    def redact_payload(self, payload: dict) -> dict:
        return payload
