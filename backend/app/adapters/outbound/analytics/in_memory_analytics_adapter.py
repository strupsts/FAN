from __future__ import annotations

from app.ports import AnalyticsEvent, AnalyticsPort


class InMemoryAnalyticsAdapter(AnalyticsPort):
    def __init__(self) -> None:
        self.events: list[AnalyticsEvent] = []

    def track(self, event: AnalyticsEvent) -> None:
        self.events.append(event)
