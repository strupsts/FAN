from __future__ import annotations

from typing import Protocol


class PrivacyRedactorPort(Protocol):
    def redact_text(self, text: str) -> str:
        """Remove or mask sensitive data from text."""
        ...

    def redact_payload(self, payload: dict) -> dict:
        """Remove or mask sensitive data from structured payload."""
        ...
