"""Analytics and aggregation agent."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


class AnalyticsAgent:
    def __init__(self) -> None:
        pass

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        """Run comprehensive analytics on a DataFrame.

        Args:
            df: Input DataFrame

        Returns:
            Dictionary with analytics results
        """
        if df.empty:
            return {"error": "Empty DataFrame"}

        return {
            "summary": self._get_summary(df),
            "numeric_columns": self._analyze_numeric(df),
            "categorical_columns": self._analyze_categorical(df),
            "correlations": self._get_correlations(df),
            "outliers": self._detect_outliers(df),
        }

    def _get_summary(self, df: pd.DataFrame) -> dict[str, Any]:
        """Get overall DataFrame summary."""
        return {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": {col: int(df[col].isna().sum()) for col in df.columns},
            "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
        }

    def _analyze_numeric(self, df: pd.DataFrame) -> dict[str, dict[str, float]]:
        """Analyze numeric columns."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        result = {}

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            result[col] = {
                "count": int(series.count()),
                "mean": float(series.mean()),
                "std": float(series.std()),
                "min": float(series.min()),
                "q25": float(series.quantile(0.25)),
                "median": float(series.median()),
                "q75": float(series.quantile(0.75)),
                "max": float(series.max()),
                "sum": float(series.sum()),
            }

        return result

    def _analyze_categorical(self, df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        """Analyze categorical/string columns."""
        cat_cols = df.select_dtypes(include=["object", "string"]).columns
        result = {}

        for col in cat_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            value_counts = series.value_counts().head(10)
            result[col] = {
                "count": int(series.count()),
                "unique": int(series.nunique()),
                "top_values": [
                    {"value": str(v), "count": int(c)}
                    for v, c in value_counts.items()
                ],
                "missing": int(df[col].isna().sum()),
            }

        return result

    def _get_correlations(self, df: pd.DataFrame) -> dict[str, dict[str, float]]:
        """Calculate correlation matrix for numeric columns."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return {}

        corr = numeric_df.corr()
        return {
            col: {row: float(corr.loc[row, col]) for row in corr.index}
            for col in corr.columns
        }

    def _detect_outliers(self, df: pd.DataFrame) -> dict[str, dict[str, Any]]:
        """Detect outliers using IQR method."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outliers = {}

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr

            outlier_mask = (series < lower) | (series > upper)
            if outlier_mask.sum() > 0:
                outliers[col] = {
                    "count": int(outlier_mask.sum()),
                    "lower_bound": float(lower),
                    "upper_bound": float(upper),
                    "values": [float(v) for v in series[outlier_mask].head(20).tolist()],
                }

        return outliers

    def aggregate(
        self,
        df: pd.DataFrame,
        group_by: str | list[str],
        agg_func: str = "sum",
        column: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate data by group.

        Args:
            df: Input DataFrame
            group_by: Column(s) to group by
            agg_func: Aggregation function (sum, mean, count, min, max, std)
            column: Column to aggregate (if None, counts)

        Returns:
            Aggregated DataFrame
        """
        if column is None:
            return df.groupby(group_by).size().reset_index(name="count")

        agg_map = {"sum": "sum", "mean": "mean", "count": "count", "min": "min", "max": "max", "std": "std"}
        func = agg_map.get(agg_func, "sum")
        return df.groupby(group_by)[column].agg(func).reset_index()

    def pivot_table(
        self,
        df: pd.DataFrame,
        index: str,
        columns: str,
        values: str,
        aggfunc: str = "sum",
    ) -> pd.DataFrame:
        """Create pivot table."""
        return pd.pivot_table(df, index=index, columns=columns, values=values, aggfunc=aggfunc, fill_value=0)

    def time_series_analysis(self, df: pd.DataFrame, date_col: str, value_col: str) -> dict[str, Any]:
        """Analyze time series data."""
        if date_col not in df.columns or value_col not in df.columns:
            return {"error": "Columns not found"}

        df_ts = df[[date_col, value_col]].copy()
        df_ts[date_col] = pd.to_datetime(df_ts[date_col], errors="coerce")
        df_ts = df_ts.dropna().sort_values(date_col)

        if len(df_ts) < 2:
            return {"error": "Insufficient data for time series analysis"}

        values = df_ts[value_col]
        return {
            "start_date": str(df_ts[date_col].min()),
            "end_date": str(df_ts[date_col].max()),
            "period_days": int((df_ts[date_col].max() - df_ts[date_col].min()).days),
            "total_records": int(len(df_ts)),
            "trend": self._calculate_trend(values),
            "moving_avg_7": float(values.rolling(7).mean().iloc[-1]) if len(values) >= 7 else None,
            "moving_avg_30": float(values.rolling(30).mean().iloc[-1]) if len(values) >= 30 else None,
        }

    def _calculate_trend(self, series: pd.Series) -> str:
        """Calculate simple trend direction."""
        if len(series) < 2:
            return "insufficient_data"
        first_half = series.iloc[:len(series)//2].mean()
        second_half = series.iloc[len(series)//2:].mean()
        if second_half > first_half * 1.05:
            return "increasing"
        elif second_half < first_half * 0.95:
            return "decreasing"
        return "stable"
