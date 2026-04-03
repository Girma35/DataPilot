"""Slack API service using OAuth tokens from Auth0 Connected Accounts."""

from __future__ import annotations

import logging
import re
from typing import Any

import requests

logger = logging.getLogger(__name__)

_SLACK_CHANNEL_ID = re.compile(r"^[CGD][A-Z0-9]{8,}$", re.IGNORECASE)


def _normalize_slack_channel(channel: str) -> str:
    """Slack chat.postMessage accepts channel ID (C…/G…/D…) or #name."""
    c = channel.strip()
    if c.startswith("#"):
        return c
    if _SLACK_CHANNEL_ID.match(c):
        return c
    return f"#{c}"


class SlackOAuthService:
    """Service to interact with Slack API using OAuth tokens."""

    def __init__(self, access_token: str | None = None) -> None:
        self._access_token = access_token
        self._base_url = "https://slack.com/api"

    def list_channels(self, limit: int = 100) -> dict[str, Any]:
        """List channels in the workspace.

        Args:
            limit: Maximum number of channels to return

        Returns:
            Dict with channels list and metadata
        """
        if not self._access_token:
            return {"error": "No access token available", "channels": []}

        try:
            response = requests.get(
                f"{self._base_url}/conversations.list",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "exclude_archived": True,
                    "types": "public_channel,private_channel",
                    "limit": limit,
                },
                timeout=30,
            )
            data = response.json()

            if not data.get("ok"):
                return {"error": data.get("error", "Unknown error"), "channels": []}

            channels = [
                {
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "is_private": ch.get("is_private", False),
                    "num_members": ch.get("num_members"),
                    "topic": ch.get("topic", {}).get("value", ""),
                    "purpose": ch.get("purpose", {}).get("value", ""),
                }
                for ch in data.get("channels", [])
            ]

            return {
                "ok": True,
                "channels": channels,
                "total": len(channels),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to list Slack channels: {e}")
            return {"error": str(e), "channels": []}

    def send_message(self, channel: str, text: str) -> dict[str, Any]:
        """Send a message to a Slack channel.

        Args:
            channel: Channel ID or name (without #)
            text: Message text to send

        Returns:
            Dict with send status
        """
        if not self._access_token:
            return {"error": "No access token available", "ok": False}

        try:
            response = requests.post(
                f"{self._base_url}/chat.postMessage",
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "channel": _normalize_slack_channel(channel),
                    "text": text,
                },
                timeout=30,
            )
            data = response.json()

            if not data.get("ok"):
                return {"error": data.get("error", "Unknown error"), "ok": False}

            return {
                "ok": True,
                "ts": data.get("ts"),
                "channel": data.get("channel"),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack message: {e}")
            return {"error": str(e), "ok": False}

    def list_messages(self, channel: str, limit: int = 10) -> dict[str, Any]:
        """List recent messages in a channel.

        Args:
            channel: Channel ID or name
            limit: Number of messages to fetch

        Returns:
            Dict with messages list
        """
        if not self._access_token:
            return {"error": "No access token available", "messages": []}

        # Resolve channel name to ID if needed
        channel_id = channel
        if not channel.startswith("C") and not channel.startswith("G"):
            channels_result = self.list_channels()
            for ch in channels_result.get("channels", []):
                if ch.get("name") == channel:
                    channel_id = ch.get("id", channel)
                    break

        try:
            response = requests.get(
                f"{self._base_url}/conversations.history",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={
                    "channel": channel_id,
                    "limit": limit,
                },
                timeout=30,
            )
            data = response.json()

            if not data.get("ok"):
                return {"error": data.get("error", "Unknown error"), "messages": []}

            messages = [
                {
                    "user": msg.get("user"),
                    "text": msg.get("text"),
                    "ts": msg.get("ts"),
                    "type": msg.get("type"),
                }
                for msg in data.get("messages", [])
            ]

            return {
                "ok": True,
                "messages": messages,
                "total": len(messages),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to list Slack messages: {e}")
            return {"error": str(e), "messages": []}


def create_slack_service(access_token: str) -> SlackOAuthService:
    """Factory function to create Slack service with token."""
    return SlackOAuthService(access_token=access_token)