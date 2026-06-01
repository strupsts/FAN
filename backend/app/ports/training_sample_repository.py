from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class TrainingSample:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    source_prediction_id: UUID | None = None
    input_payload: dict[str, Any] = field(default_factory=dict)
    target_payload: dict[str, Any] = field(default_factory=dict)
    is_sanitized: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.input_payload:
            raise ValueError("Training sample input_payload must not be empty")

        if not self.target_payload:
            raise ValueError("Training sample target_payload must not be empty")


class TrainingSampleRepositoryPort(Protocol):
    def save_training_sample(self, sample: TrainingSample) -> None:
        """Save prediction/correction pair for evals and future model improvement."""
        ...
