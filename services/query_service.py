"""Read-only query execution service (GLPI / PostgreSQL)."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy.engine import Engine

from db.connection import assert_read_only_sql, create_sync_engine, execute_read_only_query


class QueryService:
    def __init__(self, engine: Engine | None = None):
        self._engine = engine

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_sync_engine()
        return self._engine

    def validate_sql(self, sql: str) -> None:
        assert_read_only_sql(sql)

    def run_read_query(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
    ) -> Sequence[dict[str, Any]]:
        return execute_read_only_query(self.engine, sql, params)
