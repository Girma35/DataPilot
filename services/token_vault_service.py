"""Auth0 Token Vault access-token exchange (RFC8693-style) for federated connections."""

from __future__ import annotations

import logging
from typing import Any

import requests

from config import AUTH0_DOMAIN, AUTH0_TOKEN_VAULT_CLIENT_ID, AUTH0_TOKEN_VAULT_CLIENT_SECRET

logger = logging.getLogger(__name__)

# https://auth0.com/docs/secure/tokens/token-vault/access-token-exchange-with-token-vault
_GRANT_TYPE_FEDERATED = "urn:auth0:params:oauth:grant-type:token-exchange:federated-connection-access-token"
_SUBJECT_TOKEN_TYPE_ACCESS = "urn:ietf:params:oauth:token-type:access_token"
_REQUESTED_TYPE_FEDERATED = "http://auth0.com/oauth/token-type/federated-connection-access-token"


class TokenVaultService:
    """Exchange a user's Auth0 API access token for a provider token stored in Token Vault."""

    def __init__(
        self,
        domain: str | None = None,
        vault_client_id: str | None = None,
        vault_client_secret: str | None = None,
    ) -> None:
        self._domain = domain or AUTH0_DOMAIN
        self._client_id = vault_client_id or AUTH0_TOKEN_VAULT_CLIENT_ID
        self._client_secret = vault_client_secret or AUTH0_TOKEN_VAULT_CLIENT_SECRET

    def is_configured(self) -> bool:
        return bool(self._domain and self._client_id and self._client_secret)

    def exchange_federated_access_token(
        self,
        subject_token: str,
        connection: str,
        login_hint: str | None = None,
    ) -> dict[str, Any]:
        """Return Auth0 /oauth/token JSON including the provider access_token on success."""
        if not self.is_configured():
            return {
                "error": "token_vault_not_configured",
                "error_description": "Set AUTH0_TOKEN_VAULT_CLIENT_ID and AUTH0_TOKEN_VAULT_CLIENT_SECRET.",
            }

        payload: dict[str, Any] = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "grant_type": _GRANT_TYPE_FEDERATED,
            "subject_token": subject_token,
            "subject_token_type": _SUBJECT_TOKEN_TYPE_ACCESS,
            "requested_token_type": _REQUESTED_TYPE_FEDERATED,
            "connection": connection,
        }
        if login_hint:
            payload["login_hint"] = login_hint

        try:
            response = requests.post(
                f"https://{self._domain}/oauth/token",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            data = response.json()
            if not response.ok:
                logger.warning("Token Vault exchange failed: %s", data)
            return data
        except requests.RequestException as e:
            logger.error("Token Vault exchange request failed: %s", e)
            return {"error": "request_failed", "error_description": str(e)}


_vault: TokenVaultService | None = None


def get_token_vault_service() -> TokenVaultService:
    global _vault
    if _vault is None:
        _vault = TokenVaultService()
    return _vault
