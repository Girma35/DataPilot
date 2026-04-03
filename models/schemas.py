"""Pydantic schemas for API requests and responses."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = Field(default="DataPilot")


class QueryRequest(BaseModel):
    sql: str = Field(..., description="Read-only SQL to execute")
    limit: Optional[int] = Field(default=None, ge=1, le=10_000)


class QueryResponse(BaseModel):
    ok: bool
    rows: Optional[list[dict[str, Any]]] = None
    error: Optional[str] = None
    row_count: Optional[int] = None


class AlertRequest(BaseModel):
    message: str = Field(..., description="Alert message to send")
    channel: str = Field(default="both", description="Target channel: slack, discord, or both", pattern="^(slack|discord|both)$")


class AlertResponse(BaseModel):
    ok: bool
    results: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class GLPIWebhookRequest(BaseModel):
    """GLPI webhook payload received from GLPI notification system."""
    event_type: Optional[str] = Field(default=None, description="Event type (ticket.created, ticket.updated, etc.)")
    item_id: Optional[int] = Field(default=None, description="GLPI item ID")
    item_type: Optional[str] = Field(default=None, description="Item type (Ticket, Computer, etc.)")
    name: Optional[str] = Field(default=None, description="Item name/title")
    status: Optional[str] = Field(default=None, description="Current status")
    priority: Optional[int] = Field(default=None, description="Priority level (1-5)")
    category: Optional[str] = Field(default=None, description="Category name")
    entity: Optional[str] = Field(default=None, description="Entity name")
    requester: Optional[str] = Field(default=None, description="Requester name/email")
    assignee: Optional[str] = Field(default=None, description="Assigned user/group")
    description: Optional[str] = Field(default=None, description="Item description")
    date_creation: Optional[str] = Field(default=None, description="Creation date")
    date_mod: Optional[str] = Field(default=None, description="Last modification date")
    raw_payload: Optional[dict[str, Any]] = Field(default=None, description="Raw webhook payload for custom processing")


class GLPIWebhookResponse(BaseModel):
    ok: bool
    message: Optional[str] = None
    processed: bool = False
    alert_sent: bool = False
    error: Optional[str] = None
    glpi_followup_ok: Optional[bool] = None
    glpi_followup_error: Optional[str] = None
    glpi_status_updated: Optional[bool] = None
    glpi_status_error: Optional[str] = None


class ChannelGlpiAgentRequest(BaseModel):
    """Simulate a chat message for the GLPI channel agent (testing without Slack)."""

    message: str = Field(..., min_length=1)
    context_ticket_id: Optional[int] = Field(
        default=None,
        description="Default ticket if the message does not include #id",
    )


class ChannelGlpiAgentResponse(BaseModel):
    ok: bool
    action: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    glpi: Optional[dict[str, Any]] = None
    plan: Optional[dict[str, Any]] = None


class AgentSlackNotifyRequest(BaseModel):
    """Intermediary agent: post to Slack using Token Vault (user's connected Slack account)."""

    message: str = Field(..., min_length=1, description="Message text for chat.postMessage")
    slack_channel: str = Field(
        ...,
        min_length=1,
        description="Slack channel ID (e.g. C0123…) or channel name",
    )
    connection: Optional[str] = Field(
        default=None,
        description="Auth0 connection name if not the default (AUTH0_VAULT_SLACK_CONNECTION)",
    )
    login_hint: Optional[str] = Field(
        default=None,
        description="Optional login_hint when the user has multiple accounts on the same connection",
    )


class AgentSlackNotifyResponse(BaseModel):
    ok: bool
    user_sub: Optional[str] = None
    slack: Optional[dict[str, Any]] = None
    vault_meta: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    detail: Optional[str] = None
    auth0: Optional[dict[str, Any]] = None
