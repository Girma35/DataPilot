"""Placeholder alerting service for scheduled insights and thresholds."""

from __future__ import annotations

from typing import Any


class AlertService:
    def __init__(self) -> None:
        pass

    def send_placeholder(self, payload: dict[str, Any]) -> None:
        """Stub hook for future notification channels."""
        _ = payload
