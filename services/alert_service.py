"""Alert service for notifications via Slack, Discord, and other channels."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config import DISCORD_WEBHOOK_URL, SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(
        self,
        slack_webhook: str | None = None,
        discord_webhook: str | None = None,
    ) -> None:
        self._slack_webhook = slack_webhook or SLACK_WEBHOOK_URL
        self._discord_webhook = discord_webhook or DISCORD_WEBHOOK_URL

    def send(self, message: str, channel: str = "both") -> dict[str, Any]:
        """Send alert to specified channels.

        Args:
            message: The message to send
            channel: "slack", "discord", or "both" (default: "both")

        Returns:
            Dict with send status per channel
        """
        results = {}

        if channel in ("slack", "both"):
            results["slack"] = self._send_slack(message)

        if channel in ("discord", "both"):
            results["discord"] = self._send_discord(message)

        return results

    def _send_slack(self, message: str) -> dict[str, Any]:
        """Send message to Slack webhook."""
        if not self._slack_webhook:
            return {"status": "skipped", "reason": "Slack webhook not configured"}

        try:
            payload = {"text": message}
            response = requests.post(
                self._slack_webhook,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Slack alert sent successfully")
            return {"status": "success", "code": response.status_code}
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return {"status": "error", "error": str(e)}

    def _send_discord(self, message: str) -> dict[str, Any]:
        """Send message to Discord webhook."""
        if not self._discord_webhook:
            return {"status": "skipped", "reason": "Discord webhook not configured"}

        try:
            payload = {"content": message}
            response = requests.post(
                self._discord_webhook,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Discord alert sent successfully")
            return {"status": "success", "code": response.status_code}
        except requests.RequestException as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return {"status": "error", "error": str(e)}

    def send_placeholder(self, payload: dict[str, Any]) -> None:
        """Legacy method for backward compatibility."""
        event = payload.get("event", "event")
        message = f"DataPilot: {event} triggered"
        self.send(message)
