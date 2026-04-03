"""Intermediary agent: use Auth0 Token Vault so the backend acts on the user's behalf (e.g. Slack API)."""

from __future__ import annotations

import logging
from typing import Any

from config import AUTH0_VAULT_SLACK_CONNECTION
from services.slack_service import SlackOAuthService
from services.token_vault_service import get_token_vault_service

logger = logging.getLogger(__name__)


class IntermediaryAgentService:
    """Performs delegated actions using tokens from Auth0 Token Vault (no shared bot webhooks required)."""

    def notify_slack_via_token_vault(
        self,
        subject_token: str,
        message: str,
        slack_channel: str,
        connection: str | None = None,
        login_hint: str | None = None,
    ) -> dict[str, Any]:
        conn = connection or AUTH0_VAULT_SLACK_CONNECTION
        vault = get_token_vault_service()

        if not vault.is_configured():
            return {
                "ok": False,
                "error": "token_vault_not_configured",
                "detail": "Configure AUTH0_TOKEN_VAULT_CLIENT_ID and AUTH0_TOKEN_VAULT_CLIENT_SECRET in Auth0 (Token Vault + Custom API client).",
            }

        exchanged = vault.exchange_federated_access_token(
            subject_token, connection=conn, login_hint=login_hint
        )
        if exchanged.get("error"):
            return {
                "ok": False,
                "error": "token_exchange_failed",
                "auth0": {k: v for k, v in exchanged.items() if k != "access_token"},
            }

        provider_token = exchanged.get("access_token")
        if not provider_token:
            return {"ok": False, "error": "no_provider_token", "auth0": exchanged}

        slack = SlackOAuthService(access_token=provider_token)
        post = slack.send_message(slack_channel, message)
        return {
            "ok": bool(post.get("ok")),
            "slack": post,
            "vault_meta": {
                "issued_token_type": exchanged.get("issued_token_type"),
                "expires_in": exchanged.get("expires_in"),
                "scope": exchanged.get("scope"),
            },
        }


_intermediary: IntermediaryAgentService | None = None


def get_intermediary_agent_service() -> IntermediaryAgentService:
    global _intermediary
    if _intermediary is None:
        _intermediary = IntermediaryAgentService()
    return _intermediary
