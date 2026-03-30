"""SQLAlchemy engines, pooling, and read-only query execution."""

from __future__ import annotations

import re
from typing import Any, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import QueuePool

from config import DATABASE_URL

_FORBIDDEN_SQL = re.compile(
    r"\b(DELETE|DROP|UPDATE|INSERT)\b",
    re.IGNORECASE | re.DOTALL,
)


def _to_async_url(sync_url: str) -> str:
    if sync_url.startswith("postgresql+asyncpg://"):
        return sync_url
    if sync_url.startswith("postgresql://"):
        return sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if sync_url.startswith("postgres://"):
        return sync_url.replace("postgres://", "postgresql+asyncpg://", 1)
    return sync_url


def create_sync_engine() -> Engine:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    return create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
        future=True,
    )


def create_async_db_engine() -> AsyncEngine:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")
    url = _to_async_url(DATABASE_URL)
    return create_async_engine(
        url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )


def assert_read_only_sql(sql: str) -> None:
    """Reject statements that could mutate schema or data."""
    stripped = sql.strip()
    if not stripped:
        raise ValueError("Empty SQL")
    if _FORBIDDEN_SQL.search(stripped):
        raise ValueError(
            "Only read-only queries are allowed; DELETE, DROP, UPDATE, and INSERT are not permitted."
        )


def execute_read_only_query(
    engine: Engine,
    sql: str,
    params: dict[str, Any] | None = None,
) -> Sequence[dict[str, Any]]:
    """Execute a parameterized read-only query and return rows as dicts."""
    assert_read_only_sql(sql)
    bind_params = params or {}
    with engine.connect() as conn:
        result = conn.execute(text(sql), bind_params)
        keys = result.keys()
        return [dict(zip(keys, row)) for row in result.fetchall()]


async def execute_read_only_query_async(
    async_engine: AsyncEngine,
    sql: str,
    params: dict[str, Any] | None = None,
) -> Sequence[dict[str, Any]]:
    assert_read_only_sql(sql)
    bind_params = params or {}
    async with async_engine.connect() as conn:
        result = await conn.execute(text(sql), bind_params)
        keys = result.keys()
        rows = result.fetchall()
        return [dict(zip(keys, row)) for row in rows]
