"""Data loading and preparation agent."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from services.query_service import QueryService

_VALID_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$")


class DataAgent:
    def __init__(self, query_service: QueryService | None = None) -> None:
        self._service = query_service or QueryService()

    @property
    def service(self) -> QueryService:
        return self._service

    def run(
        self,
        sql: str | None = None,
        table_name: str | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch and normalize data from PostgreSQL.

        Args:
            sql: Raw SQL query to execute (read-only only)
            table_name: Table name to fetch (alternative to sql)
            limit: Optional row limit

        Returns:
            Normalized pandas DataFrame
        """
        if sql is None and table_name is None:
            raise ValueError("Either 'sql' or 'table_name' must be provided")

        if table_name is not None:
            self._validate_identifier(table_name)
            sql = f"SELECT * FROM {table_name}"
            if limit:
                sql = f"SELECT * FROM {table_name} LIMIT {limit}"

        rows = self._service.run_read_query(sql)
        df = self._normalize(pd.DataFrame(rows))
        return df

    def _validate_identifier(self, name: str) -> None:
        """Validate that a table/column name is a safe identifier."""
        if not _VALID_IDENTIFIER.match(name):
            raise ValueError(f"Invalid identifier: {name}")

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize DataFrame: clean data, handle types, fill missing."""
        if df.empty:
            return df

        df = df.copy()

        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].fillna("").astype(str).str.strip()
                df.loc[df[col] == "", col] = None

        df = df.infer_objects(copy=False)

        return df

    def get_table_schema(self, table_name: str) -> list[dict[str, Any]]:
        """Get column information for a table."""
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """
        rows = self._service.run_read_query(sql, {"table_name": table_name})
        return list(rows)

    def list_tables(self, schema: str = "public") -> list[str]:
        """List all tables in a schema."""
        sql = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = :schema ORDER BY table_name
        """
        rows = self._service.run_read_query(sql, {"schema": schema})
        return [row["table_name"] for row in rows]

    def fetch_sample(
        self,
        table_name: str,
        sample_size: int = 100,
    ) -> pd.DataFrame:
        """Fetch a random sample of rows from a table."""
        self._validate_identifier(table_name)
        sql = f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {sample_size}"
        rows = self._service.run_read_query(sql)
        return self._normalize(pd.DataFrame(rows))
