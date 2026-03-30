"""Agent that turns natural language into validated read-only SQL (stub)."""

from typing import Any, Sequence

from services.query_service import QueryService


class QueryAgent:
    def __init__(self, query_service: QueryService | None = None):
        self._service = query_service or QueryService()

    def execute(self, sql: str, params: dict[str, Any] | None = None) -> Sequence[dict[str, Any]]:
        """Run a read-only SQL statement via QueryService."""
        return self._service.run_read_query(sql, params)
