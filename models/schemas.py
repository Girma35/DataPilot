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
