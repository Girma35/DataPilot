"""Discord API service using OAuth tokens from Auth0 Connected Accounts."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class DiscordOAuthService:
    """Service to interact with Discord API using OAuth tokens."""

    def __init__(self, access_token: str | None = None) -> None:
        self._access_token = access_token
        self._base_url = "https://discord.com/api/v10"

    def _headers(self) -> dict[str, str]:
        """Get headers with authorization."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def list_guilds(self) -> dict[str, Any]:
        """List guilds (servers) the user is a member of.

        Returns:
            Dict with guilds list
        """
        if not self._access_token:
            return {"error": "No access token available", "guilds": []}

        try:
            response = requests.get(
                f"{self._base_url}/users/@me/guilds",
                headers=self._headers(),
                timeout=30,
            )
            data = response.json()

            if isinstance(data, dict) and "message" in data:
                return {"error": data.get("message"), "guilds": []}

            guilds = [
                {
                    "id": g.get("id"),
                    "name": g.get("name"),
                    "icon": g.get("icon"),
                    "owner": g.get("owner_id"),
                    "permissions": g.get("permissions"),
                }
                for g in data
            ]

            return {
                "ok": True,
                "guilds": guilds,
                "total": len(guilds),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to list Discord guilds: {e}")
            return {"error": str(e), "guilds": []}

    def get_guild_channels(self, guild_id: str) -> dict[str, Any]:
        """Get channels in a guild.

        Args:
            guild_id: Discord guild (server) ID

        Returns:
            Dict with channels list
        """
        if not self._access_token:
            return {"error": "No access token available", "channels": []}

        try:
            response = requests.get(
                f"{self._base_url}/guilds/{guild_id}/channels",
                headers=self._headers(),
                timeout=30,
            )
            data = response.json()

            if isinstance(data, dict) and "message" in data:
                return {"error": data.get("message"), "channels": []}

            # Filter to text channels
            text_channels = [
                {
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "type": ch.get("type"),
                    "position": ch.get("position"),
                    "parent_id": ch.get("parent_id"),
                }
                for ch in data if ch.get("type") == 0  # 0 = text channel
            ]

            return {
                "ok": True,
                "channels": text_channels,
                "total": len(text_channels),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to get Discord channels: {e}")
            return {"error": str(e), "channels": []}

    def send_message(self, channel_id: str, text: str) -> dict[str, Any]:
        """Send a message to a Discord channel.

        Args:
            channel_id: Discord channel ID
            text: Message text to send

        Returns:
            Dict with send status
        """
        if not self._access_token:
            return {"error": "No access token available", "ok": False}

        try:
            response = requests.post(
                f"{self._base_url}/channels/{channel_id}/messages",
                headers=self._headers(),
                json={"content": text},
                timeout=30,
            )
            data = response.json()

            if "message" in data:
                return {"error": data.get("message"), "ok": False}

            return {
                "ok": True,
                "id": data.get("id"),
                "channel_id": data.get("channel_id"),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to send Discord message: {e}")
            return {"error": str(e), "ok": False}

    def list_messages(self, channel_id: str, limit: int = 10) -> dict[str, Any]:
        """List recent messages in a channel.

        Args:
            channel_id: Discord channel ID
            limit: Number of messages to fetch

        Returns:
            Dict with messages list
        """
        if not self._access_token:
            return {"error": "No access token available", "messages": []}

        try:
            response = requests.get(
                f"{self._base_url}/channels/{channel_id}/messages",
                headers=self._headers(),
                params={"limit": limit},
                timeout=30,
            )
            data = response.json()

            if isinstance(data, dict) and "message" in data:
                return {"error": data.get("message"), "messages": []}

            messages = [
                {
                    "id": msg.get("id"),
                    "author": msg.get("author", {}).get("username"),
                    "content": msg.get("content"),
                    "timestamp": msg.get("timestamp"),
                }
                for msg in data
            ]

            return {
                "ok": True,
                "messages": messages,
                "total": len(messages),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to list Discord messages: {e}")
            return {"error": str(e), "messages": []}

    def get_current_user(self) -> dict[str, Any]:
        """Get current user info.

        Returns:
            Dict with user info
        """
        if not self._access_token:
            return {"error": "No access token available"}

        try:
            response = requests.get(
                f"{self._base_url}/users/@me",
                headers=self._headers(),
                timeout=30,
            )
            data = response.json()

            if "message" in data:
                return {"error": data.get("message")}

            return {
                "ok": True,
                "id": data.get("id"),
                "username": data.get("username"),
                "discriminator": data.get("discriminator"),
                "global_name": data.get("global_name"),
            }
        except requests.RequestException as e:
            logger.error(f"Failed to get Discord user: {e}")
            return {"error": str(e)}


def create_discord_service(access_token: str) -> DiscordOAuthService:
    """Factory function to create Discord service with token."""
    return DiscordOAuthService(access_token=access_token)