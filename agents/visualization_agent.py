"""Chart and report generation agent."""

from __future__ import annotations

import base64
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class VisualizationAgent:
    def __init__(self) -> None:
        pass

    def run(
        self,
        df: pd.DataFrame,
        chart_type: str = "auto",
        x: str | None = None,
        y: str | None = None,
        title: str = "Data Visualization",
    ) -> dict[str, Any]:
        """Generate visualization from DataFrame.

        Args:
            df: Input DataFrame
            chart_type: Type of chart (auto, bar, line, scatter, pie, histogram, box)
            x: X-axis column
            y: Y-axis column
            title: Chart title

        Returns:
            Dict with chart data and base64-encoded image
        """
        if df.empty:
            return {"error": "Empty DataFrame"}

        if chart_type == "auto":
            chart_type = self._infer_chart_type(df, x, y)

        chart_data = self._create_chart(df, chart_type, x, y, title)
        return chart_data

    def _infer_chart_type(self, df: pd.DataFrame, x: str | None, y: str | None) -> str:
        """Infer best chart type based on data."""
        if x and y:
            if y in df.columns and df[y].dtype in ["int64", "float64"]:
                if x in df.columns and df[x].dtype in ["int64", "float64"]:
                    return "scatter"
                return "bar"
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        if len(numeric_cols) > 0:
            return "histogram"
        return "bar"

    def _create_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x: str | None,
        y: str | None,
        title: str,
    ) -> dict[str, Any]:
        """Create chart based on type."""
        methods = {
            "bar": self._create_bar_chart,
            "line": self._create_line_chart,
            "scatter": self._create_scatter_chart,
            "pie": self._create_pie_chart,
            "histogram": self._create_histogram,
            "box": self._create_box_plot,
        }

        method = methods.get(chart_type, self._create_bar_chart)
        return method(df, x, y, title)

    def _create_bar_chart(self, df: pd.DataFrame, x: str | None, y: str | None, title: str) -> dict[str, Any]:
        """Create bar chart."""
        x_col = x or df.columns[0]
        y_col = y or (df.select_dtypes(include=["int64", "float64"]).columns[0] if len(df.select_dtypes(include=["int64", "float64"]).columns) > 0 else None)

        if y_col:
            fig = px.bar(df, x=x_col, y=y_col, title=title)
        else:
            fig = px.bar(df, x=x_col, title=title)

        return self._fig_to_response(fig, title)

    def _create_line_chart(self, df: pd.DataFrame, x: str | None, y: str | None, title: str) -> dict[str, Any]:
        """Create line chart."""
        x_col = x or df.columns[0]
        numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
        y_col = y or (numeric_cols[0] if len(numeric_cols) > 0 else None)

        if y_col:
            fig = px.line(df, x=x_col, y=y_col, title=title)
        else:
            return {"error": "No numeric column found for y-axis"}

        return self._fig_to_response(fig, title)

    def _create_scatter_chart(self, df: pd.DataFrame, x: str | None, y: str | None, title: str) -> dict[str, Any]:
        """Create scatter chart."""
        numeric_cols = list(df.select_dtypes(include=["int64", "float64"]).columns)
        if len(numeric_cols) < 2:
            return {"error": "Need at least 2 numeric columns for scatter plot"}

        x_col = x or numeric_cols[0]
        y_col = y or numeric_cols[1]

        fig = px.scatter(df, x=x_col, y=y_col, title=title, trendline="ols")
        return self._fig_to_response(fig, title)

    def _create_pie_chart(self, df: pd.DataFrame, x: str | None, y: str | None, title: str) -> dict[str, Any]:
        """Create pie chart."""
        x_col = x or df.columns[0]
        y_col = y or None

        if y_col and df[y_col].dtype in ["int64", "float64"]:
            fig = px.pie(df, names=x_col, values=y_col, title=title)
        else:
            counts = df[x_col].value_counts().reset_index()
            counts.columns = [x_col, "count"]
            fig = px.pie(counts, names=x_col, values="count", title=title)

        return self._fig_to_response(fig, title)

    def _create_histogram(self, df: pd.DataFrame, x: str | None, y: str | None, title: str) -> dict[str, Any]:
        """Create histogram."""
        numeric_cols = list(df.select_dtypes(include=["int64", "float64"]).columns)
        if not numeric_cols:
            return {"error": "No numeric columns found"}

        x_col = x or numeric_cols[0]
        fig = px.histogram(df, x=x_col, title=title, nbins=30)
        return self._fig_to_response(fig, title)

    def _create_box_plot(self, df: pd.DataFrame, x: str | None, y: str | None, title: str) -> dict[str, Any]:
        """Create box plot."""
        numeric_cols = list(df.select_dtypes(include=["int64", "float64"]).columns)
        if not numeric_cols:
            return {"error": "No numeric columns found"}

        y_col = y or numeric_cols[0]
        x_col = x or None

        fig = px.box(df, x=x_col, y=y_col, title=title)
        return self._fig_to_response(fig, title)

    def _fig_to_response(self, fig: go.Figure, title: str) -> dict[str, Any]:
        """Convert Plotly figure to response dict."""
        html = fig.to_html(full=False, include_plotlyjs="cdn")
        json_data = fig.to_json()

        img_bytes = fig.to_image(format="png", width=1200, height=600)
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")

        return {
            "title": title,
            "html": html,
            "json": json_data,
            "image_base64": f"data:image/png;base64,{img_b64}",
        }

    def create_dashboard(self, df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
        """Create multi-chart dashboard.

        Args:
            df: Input DataFrame
            config: Dashboard config with charts list

        Returns:
            Dict with dashboard HTML and images
        """
        charts = []

        for chart_conf in config.get("charts", []):
            result = self.run(
                df,
                chart_type=chart_conf.get("type", "auto"),
                x=chart_conf.get("x"),
                y=chart_conf.get("y"),
                title=chart_conf.get("title", "Chart"),
            )
            charts.append(result)

        dashboard_html = f"<html><head><title>Dashboard</title></head><body>"
        dashboard_html += "<h1>DataPilot Dashboard</h1>"
        for chart in charts:
            if "html" in chart:
                dashboard_html += f"<div>{chart['html']}</div>"
        dashboard_html += "</body></html>"

        return {
            "html": dashboard_html,
            "charts": charts,
            "chart_count": len(charts),
        }

    def generate_summary_report(self, df: pd.DataFrame, analytics: dict[str, Any]) -> str:
        """Generate text summary report from analytics.

        Args:
            df: Input DataFrame
            analytics: Analytics results from AnalyticsAgent

        Returns:
            Markdown-formatted report
        """
        lines = ["# Data Summary Report", ""]

        if "summary" in analytics:
            s = analytics["summary"]
            lines.append(f"## Overview")
            lines.append(f"- **Total Rows:** {s.get('rows', 'N/A')}")
            lines.append(f"- **Total Columns:** {s.get('columns', 'N/A')}")
            lines.append(f"- **Memory Usage:** {s.get('memory_usage_bytes', 0) / 1024:.1f} KB")
            lines.append("")

        if "numeric_columns" in analytics:
            lines.append("## Numeric Analysis")
            for col, stats in analytics["numeric_columns"].items():
                lines.append(f"### {col}")
                lines.append(f"- Mean: {stats.get('mean', 0):.2f}")
                lines.append(f"- Median: {stats.get('median', 0):.2f}")
                lines.append(f"- Std Dev: {stats.get('std', 0):.2f}")
                lines.append(f"- Range: {stats.get('min', 0):.2f} to {stats.get('max', 0):.2f}")
                lines.append("")

        if "categorical_columns" in analytics:
            lines.append("## Categorical Analysis")
            for col, stats in analytics["categorical_columns"].items():
                lines.append(f"### {col}")
                lines.append(f"- Unique Values: {stats.get('unique', 0)}")
                lines.append(f"- Top Values: {', '.join([f'{v['value']} ({v['count']})' for v in stats.get('top_values', [])[:5]])}")
                lines.append("")

        if "outliers" in analytics and analytics["outliers"]:
            lines.append("## Outliers Detected")
            for col, data in analytics["outliers"].items():
                lines.append(f"- **{col}:** {data.get('count', 0)} outliers detected")
            lines.append("")

        return "\n".join(lines)
