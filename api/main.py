"""FastAPI entrypoint for the DataPilot AI Data Analyst Agent system."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure project root is importable (e.g. uvicorn --reload worker process).
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi import FastAPI, HTTPException

from agents.insight_agent import InsightAgent
from agents.query_agent import QueryAgent
from models.schemas import HealthResponse, QueryRequest, QueryResponse
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
