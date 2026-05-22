from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class Correction:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    receipt_id: UUID | None = None
    field_name: str = ""
    original_value: str | None = None
    corrected_value: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.field_name.strip():
            raise ValueError("Correction field_name must not be empty")

        if self.original_value == self.corrected_value:
            raise ValueError("Correction must change the original value")


@dataclass(frozen=True)
class CorrectionMemory:
    user_id: UUID
    normalized_item_name: str
    chosen_category: str
    chosen_bucket: str
    merchant_name: str | None = None
    times_seen: int = 1
    last_used_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.normalized_item_name.strip():
            raise ValueError("Normalized item name must not be empty")

        if self.times_seen < 1:
            raise ValueError("times_seen must be at least 1")
