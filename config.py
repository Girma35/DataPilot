"""Application configuration loaded from environment variables."""

from pathlib import Path

from dotenv import load_dotenv
import os

# Always load repo-root .env (uvicorn cwd is often arbitrary)
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", str(Path(__file__).resolve().parent / "chroma"))

SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
# Slack Events API (incoming channel messages → GLPI agent). Create app → Event Subscriptions → this URL.
SLACK_SIGNING_SECRET: str = os.getenv("SLACK_SIGNING_SECRET", "")
# Comma-separated channel IDs to process (empty = all non-DM channels that send events)
SLACK_EVENTS_CHANNEL_IDS: str = os.getenv("SLACK_EVENTS_CHANNEL_IDS", "").strip()

# LLM Provider: "openai" or "groq"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")
LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# Auth0 Configuration
AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID: str = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET: str = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_CALLBACK_URL: str = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:3000/api/auth/callback")
# Must be your DataPilot Custom API identifier (same as NEXT_PUBLIC_AUTH0_AUDIENCE). Not Management API.
AUTH0_AUDIENCE: str = os.getenv("AUTH0_AUDIENCE", "")

# Connected Accounts API
CONNECTED_ACCOUNTS_AUDIENCE: str = os.getenv("CONNECTED_ACCOUNTS_AUDIENCE", "")

# GLPI REST API (optional — add follow-up / status when a webhook fires)
GLPI_API_URL: str = os.getenv("GLPI_API_URL", "").rstrip("/")
GLPI_APP_TOKEN: str = os.getenv("GLPI_APP_TOKEN", "")
GLPI_USER_TOKEN: str = os.getenv("GLPI_USER_TOKEN", "")
# After notifying Slack/Discord, append this follow-up to the ticket (HTML-safe text)
GLPI_WEBHOOK_ADD_FOLLOWUP: bool = os.getenv("GLPI_WEBHOOK_ADD_FOLLOWUP", "true").lower() in (
    "1",
    "true",
    "yes",
)
# Optional: set ticket status ID after notify (empty = skip; IDs depend on your GLPI)
GLPI_WEBHOOK_STATUS_ID: str = os.getenv("GLPI_WEBHOOK_STATUS_ID", "").strip()
# open_only = only new/open/reopen tickets get Slack/Discord + GLPI follow-up; all = previous broad list
GLPI_WEBHOOK_EVENTS_MODE: str = os.getenv("GLPI_WEBHOOK_EVENTS_MODE", "open_only").strip().lower()

# Auth0 Token Vault — Custom API client (enable "Token Vault" grant + link to your Resource API)
# See https://auth0.com/docs/secure/tokens/token-vault/configure-token-vault
AUTH0_TOKEN_VAULT_CLIENT_ID: str = os.getenv("AUTH0_TOKEN_VAULT_CLIENT_ID", "")
AUTH0_TOKEN_VAULT_CLIENT_SECRET: str = os.getenv("AUTH0_TOKEN_VAULT_CLIENT_SECRET", "")
# Auth0 connection name with Connected Accounts + Token Vault enabled (e.g. slack)
AUTH0_VAULT_SLACK_CONNECTION: str = os.getenv("AUTH0_VAULT_SLACK_CONNECTION", "slack")

