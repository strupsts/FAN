from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AnalyticsEvent:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    user_id: UUID | None = None
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Analytics event name must not be empty")


class AnalyticsPort(Protocol):
    def track(self, event: AnalyticsEvent) -> None:
        """Track product event without sensitive receipt contents."""
        ...
