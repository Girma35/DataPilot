"""OAuth token service for Auth0 Connected Accounts."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config import AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_AUDIENCE

logger = logging.getLogger(__name__)


class OAuthService:
    """Service to manage OAuth tokens from Auth0 Connected Accounts."""

    def __init__(
        self,
        domain: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        audience: str | None = None,
    ) -> None:
        self._domain = domain or AUTH0_DOMAIN
        self._client_id = client_id or AUTH0_CLIENT_ID
        self._client_secret = client_secret or AUTH0_CLIENT_SECRET
        self._audience = audience or AUTH0_AUDIENCE

    def get_access_token(self, code: str, redirect_uri: str) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Dict containing access_token, token_type, expires_in, etc.
        """
        if not all([self._domain, self._client_id, self._client_secret]):
            return {"error": "Auth0 not configured"}

        try:
            response = requests.post(
                f"https://{self._domain}/oauth/token",
                json={
                    "grant_type": "authorization_code",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get access token: {e}")
            return {"error": str(e)}

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an access token using refresh token.

        Args:
            refresh_token: The refresh token

        Returns:
            Dict containing new access_token, etc.
        """
        if not all([self._domain, self._client_id, self._client_secret]):
            return {"error": "Auth0 not configured"}

        try:
            response = requests.post(
                f"https://{self._domain}/oauth/token",
                json={
                    "grant_type": "refresh_token",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                },
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to refresh token: {e}")
            return {"error": str(e)}

    def get_connected_accounts(self, access_token: str) -> list[dict[str, Any]]:
        """Get list of connected accounts for the user.

        Args:
            access_token: Access token with read:me:connected_accounts scope

        Returns:
            List of connected account objects
        """
        if not self._domain:
            return []

        try:
            base_url = f"https://{self._domain}/me/v1/connected-accounts/accounts"
            response = requests.get(
                base_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if response.ok:
                data = response.json()
                return data.get("accounts", [])
            return []
        except requests.RequestException as e:
            logger.error(f"Failed to get connected accounts: {e}")
            return []

    def get_connection_token(self, access_token: str, connection: str) -> dict[str, Any]:
        """Get OAuth token for a specific connected account.

        Args:
            access_token: User's access token
            connection: Connection name (e.g., "slack", "discord", "github")

        Returns:
            Dict containing the connection's access token
        """
        if not self._domain:
            return {"error": "Auth0 not configured"}

        try:
            base_url = f"https://{self._domain}/me/v1/connected-accounts/accounts"
            response = requests.get(
                base_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            if response.ok:
                accounts = response.json().get("accounts", [])
                for account in accounts:
                    if account.get("connection", "").lower() == connection.lower():
                        return {
                            "access_token": account.get("access_token"),
                            "expires_at": account.get("expires_at"),
                            "scopes": account.get("scopes", []),
                        }
                return {"error": f"No connected account found for {connection}"}
            return {"error": "Failed to fetch accounts"}
        except requests.RequestException as e:
            logger.error(f"Failed to get connection token: {e}")
            return {"error": str(e)}


# Singleton instance
_oauth_service: OAuthService | None = None


def get_oauth_service() -> OAuthService:
    """Get or create OAuth service singleton."""
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service