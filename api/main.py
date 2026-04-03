"""FastAPI entrypoint for the DataPilot AI Data Analyst Agent system."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is importable (e.g. uvicorn --reload worker process).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import json
import logging

from fastapi import Depends, FastAPI, HTTPException, Request

logger = logging.getLogger(__name__)

from agents.insight_agent import InsightAgent
from agents.query_agent import QueryAgent
from models.schemas import (
    AgentSlackNotifyRequest,
    AgentSlackNotifyResponse,
    AlertRequest,
    AlertResponse,
    ChannelGlpiAgentRequest,
    ChannelGlpiAgentResponse,
    GLPIWebhookResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
)
from services.alert_service import AlertService
from services.auth_service import get_current_user, get_current_user_with_subject_token, TokenPayload
from services.intermediary_agent_service import get_intermediary_agent_service
from config import SLACK_SIGNING_SECRET
from services.glpi_channel_agent import get_glpi_channel_agent
from services.glpi_webhook_service import get_glpi_webhook_service
from services.query_service import QueryService
from services.slack_event_dedup import should_skip_slack_delivery
from services.slack_events_verify import (
    slack_events_channel_allowed,
    slack_message_plain_text,
    verify_slack_signature,
)

_insight_agent: InsightAgent | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _insight_agent
    _insight_agent = InsightAgent()
    _insight_agent.start_scheduler()
    yield
    if _insight_agent is not None:
        _insight_agent.shutdown_scheduler(wait=False)


app = FastAPI(
    title="DataPilot",
    description="AI Data Analyst Agent API (GLPI / PostgreSQL)",
    lifespan=lifespan,
)

_query_agent = QueryAgent(QueryService())
_alert_service = AlertService()
_glpi_webhook_service = get_glpi_webhook_service(alert_service=_alert_service)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "DataPilot",
        "docs": "/docs",
        "health": "/health",
        "query": "POST /query",
        "agent_slack_token_vault": "POST /agent/slack",
        "webhook_glpi": "POST /webhook/glpi",
        "slack_events": "POST /integrations/slack/events",
        "channel_glpi_agent": "POST /agent/glpi/channel-message",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/query", response_model=QueryResponse)
def run_query(body: QueryRequest, user: TokenPayload = Depends(get_current_user)) -> QueryResponse:
    sql = body.sql
    try:
        rows = list(_query_agent.execute(sql))
        if body.limit is not None:
            rows = rows[: body.limit]
        return QueryResponse(ok=True, rows=rows, row_count=len(rows))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post(
    "/agent/slack",
    response_model=AgentSlackNotifyResponse,
    summary="Intermediary agent — Slack via Auth0 Token Vault",
)
def agent_notify_slack_token_vault(
    body: AgentSlackNotifyRequest,
    ctx: tuple[TokenPayload, str] = Depends(get_current_user_with_subject_token),
) -> AgentSlackNotifyResponse:
    """Exchange the caller's Auth0 access token for a Slack token in Token Vault, then post as the user."""
    user, subject_token = ctx
    agent = get_intermediary_agent_service()
    result = agent.notify_slack_via_token_vault(
        subject_token=subject_token,
        message=body.message,
        slack_channel=body.slack_channel,
        connection=body.connection,
        login_hint=body.login_hint,
    )
    if result.get("ok"):
        return AgentSlackNotifyResponse(
            ok=True,
            user_sub=user.sub,
            slack=result.get("slack"),
            vault_meta=result.get("vault_meta"),
        )
    raise HTTPException(
        status_code=502,
        detail={
            "ok": False,
            "user_sub": user.sub,
            "error": result.get("error"),
            "detail": result.get("detail"),
            "auth0": result.get("auth0"),
            "slack": result.get("slack"),
        },
    )


@app.post("/alert", response_model=AlertResponse)
def send_alert(body: AlertRequest, user: TokenPayload = Depends(get_current_user)) -> AlertResponse:
    """Send alert notification to Slack and/or Discord."""
    channel = body.channel.lower()
    if channel not in ("slack", "discord", "both"):
        raise HTTPException(status_code=400, detail="Invalid channel. Use: slack, discord, or both")
    try:
        results = _alert_service.send(body.message, channel)
        return AlertResponse(ok=True, results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/integrations/slack/events")
async def slack_events(request: Request) -> dict:
    """Slack Events API: URL verification + message events → GLPI channel agent."""
    if not SLACK_SIGNING_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Set SLACK_SIGNING_SECRET and subscribe this URL in the Slack app (Event Subscriptions).",
        )
    raw = await request.body()
    ts = request.headers.get("X-Slack-Request-Timestamp", "")
    sig = request.headers.get("X-Slack-Signature", "")
    if not verify_slack_signature(
        signing_secret=SLACK_SIGNING_SECRET,
        timestamp=ts,
        raw_body=raw,
        slack_signature=sig,
    ):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge", "")}

    if data.get("type") != "event_callback":
        return {"ok": True}

    if should_skip_slack_delivery(data.get("event_id")):
        return {"ok": True}

    ev = data.get("event") or {}
    if ev.get("bot_id") or ev.get("subtype") in ("bot_message", "message_changed", "message_deleted"):
        return {"ok": True}
    if ev.get("type") != "message":
        return {"ok": True}

    channel = ev.get("channel")
    if not slack_events_channel_allowed(channel):
        return {"ok": True}

    text = slack_message_plain_text(ev.get("text") or "")
    if not text:
        return {"ok": True}

    agent = get_glpi_channel_agent()
    result = agent.run(text)
    logger.info("Slack message handled by GLPI channel agent: %s", result)
    return {"ok": True}


@app.post("/agent/glpi/channel-message", response_model=ChannelGlpiAgentResponse)
def channel_glpi_agent_test(body: ChannelGlpiAgentRequest) -> ChannelGlpiAgentResponse:
    """Test the channel→GLPI agent without Slack (same logic as Slack Events)."""
    agent = get_glpi_channel_agent()
    raw = agent.run(body.message, context_ticket_id=body.context_ticket_id)
    return ChannelGlpiAgentResponse(
        ok=bool(raw.get("ok")),
        action=raw.get("action"),
        error=raw.get("error"),
        message=raw.get("message"),
        glpi=raw.get("glpi"),
        plan=raw.get("plan"),
    )


@app.post("/webhook/glpi", response_model=GLPIWebhookResponse)
def receive_glpi_webhook(body: dict) -> GLPIWebhookResponse:
    """Receive and process GLPI webhook notifications.
    
    GLPI can be configured to send webhook notifications to this endpoint.
    The service will parse the payload and optionally forward to Slack/Discord.
    
    Example GLPI webhook payload (customizable in GLPI):
    ```json
    {
        "event": "ticket.created",
        "id": 1234,
        "name": "Printer not working",
        "priority": 3,
        "status": "new",
        "category": "Hardware",
        "requester": "john@example.com"
    }
    ```
    """
    try:
        result = _glpi_webhook_service.process_webhook(body, forward_to_alert=True)
        return result
    except Exception as e:
        logger.error(f"Error processing GLPI webhook: {e}")
        return GLPIWebhookResponse(ok=False, error=str(e))
