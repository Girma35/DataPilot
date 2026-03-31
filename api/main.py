"""FastAPI entrypoint for the DataPilot AI Data Analyst Agent system."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is importable (e.g. uvicorn --reload worker process).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import logging

from fastapi import FastAPI, HTTPException

from agents.insight_agent import InsightAgent
from agents.query_agent import QueryAgent
from models.schemas import AlertRequest, AlertResponse, GLPIWebhookRequest, GLPIWebhookResponse, HealthResponse, QueryRequest, QueryResponse
from services.alert_service import AlertService
from services.glpi_webhook_service import get_glpi_webhook_service
from services.query_service import QueryService

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
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/query", response_model=QueryResponse)
def run_query(body: QueryRequest) -> QueryResponse:
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


@app.post("/alert", response_model=AlertResponse)
def send_alert(body: AlertRequest) -> AlertResponse:
    """Send alert notification to Slack and/or Discord."""
    channel = body.channel.lower()
    if channel not in ("slack", "discord", "both"):
        raise HTTPException(status_code=400, detail="Invalid channel. Use: slack, discord, or both")
    try:
        results = _alert_service.send(body.message, channel)
        return AlertResponse(ok=True, results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


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
