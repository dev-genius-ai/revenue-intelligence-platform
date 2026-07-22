"""Read-only DuckDB helpers for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "warehouse.duckdb"


def get_db_path() -> Path:
    return DEFAULT_DB_PATH


def _connect() -> duckdb.DuckDBPyConnection:
    db_path = get_db_path()
    if not db_path.is_file():
        raise FileNotFoundError(
            f"DuckDB warehouse not found at {db_path}. "
            "Run ingestion, dbt, and forecasting first."
        )
    return duckdb.connect(str(db_path), read_only=True)


@st.cache_data(show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    """Execute a read-only SQL query against warehouse.duckdb."""
    connection = _connect()
    try:
        return connection.execute(sql).fetchdf()
    finally:
        connection.close()


@st.cache_data(show_spinner=False)
def load_filter_options() -> dict[str, pd.DataFrame]:
    return {
        "companies": run_query(
            """
            SELECT company_id, company_name
            FROM analytics.company_revenue_analysis
            ORDER BY company_name
            """
        ),
        "channels": run_query(
            """
            SELECT channel_key, channel_name
            FROM analytics.channel_performance
            ORDER BY channel_name
            """
        ),
    }


@st.cache_data(show_spinner=False)
def load_channel_performance_raw() -> pd.DataFrame:
    return run_query("SELECT * FROM analytics.channel_performance")


@st.cache_data(show_spinner=False)
def load_campaign_performance_raw() -> pd.DataFrame:
    return run_query("SELECT * FROM analytics.campaign_performance")


@st.cache_data(show_spinner=False)
def load_company_analysis_raw() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM analytics.company_revenue_analysis
        ORDER BY total_revenue DESC
        """
    )


@st.cache_data(show_spinner=False)
def load_monthly_revenue_raw() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            month_start_date AS month,
            total_revenue,
            active_customers,
            new_customers
        FROM analytics.monthly_revenue_customer_growth
        ORDER BY month_start_date
        """
    )


@st.cache_data(show_spinner=False)
def load_forecast() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            month,
            predicted_revenue,
            lower_bound,
            upper_bound,
            model_name,
            generated_at
        FROM forecasting.revenue_forecast
        ORDER BY month
        """
    )


@st.cache_data(show_spinner=False)
def load_channel_anomalies() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            anomalies.month_start_date,
            anomalies.channel,
            COALESCE(channels.channel_name, anomalies.channel) AS channel_name,
            anomalies.monthly_revenue,
            anomalies.expected_revenue,
            anomalies.revenue_difference,
            anomalies.rolling_mean,
            anomalies.rolling_std,
            anomalies.z_score,
            anomalies.deviation_percent,
            anomalies.is_anomaly,
            anomalies.severity,
            anomalies.anomaly_direction,
            anomalies.anomaly_rank,
            anomalies.explanation
        FROM anomaly.channel_revenue_anomalies AS anomalies
        LEFT JOIN analytics.channel_performance AS channels
            ON anomalies.channel = channels.channel_key
        WHERE lower(anomalies.channel) <> 'unknown'
        ORDER BY
            ABS(anomalies.z_score) DESC NULLS LAST,
            anomalies.anomaly_rank ASC NULLS LAST,
            anomalies.month_start_date,
            anomalies.channel
        """
    )


@st.cache_data(show_spinner=False)
def load_attributed_revenue_raw() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            f.revenue_id,
            f.user_id,
            f.company_id,
            c.company_name,
            t.date_day AS revenue_month,
            f.first_touch_channel,
            f.last_touch_channel,
            f.revenue_amount
        FROM marts.fct_attributed_revenue AS f
        INNER JOIN marts.dim_company AS c
            ON f.company_id = c.company_id
        INNER JOIN marts.dim_time AS t
            ON f.revenue_date_key = t.date_key
        """
    )


def _selected(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if not values:
        return []
    return list(values)


def filter_channel_performance(
    company_ids: list[str] | None = None,
    channel_keys: list[str] | None = None,
) -> pd.DataFrame:
    company_ids = _selected(company_ids)
    channel_keys = _selected(channel_keys)
    base = load_channel_performance_raw().copy()

    if not company_ids:
        frame = base
    else:
        revenue = load_attributed_revenue_raw()
        revenue = revenue[revenue["company_id"].isin(company_ids)]
        first = (
            revenue.groupby("first_touch_channel", as_index=False)
            .agg(
                first_touch_revenue=("revenue_amount", "sum"),
                first_touch_customers=("user_id", "nunique"),
            )
            .rename(columns={"first_touch_channel": "channel_key"})
        )
        last = (
            revenue.groupby("last_touch_channel", as_index=False)
            .agg(
                last_touch_revenue=("revenue_amount", "sum"),
                last_touch_customers=("user_id", "nunique"),
            )
            .rename(columns={"last_touch_channel": "channel_key"})
        )
        frame = base[
            [
                "channel_key",
                "channel_name",
                "channel_group",
                "campaign_budget_usd",
                "click_through_rate",
                "views",
                "clicks",
                "campaign_count",
            ]
        ].merge(first, on="channel_key", how="left").merge(last, on="channel_key", how="left")
        for column in [
            "first_touch_revenue",
            "last_touch_revenue",
            "first_touch_customers",
            "last_touch_customers",
        ]:
            frame[column] = frame[column].fillna(0)

    if channel_keys:
        frame = frame[frame["channel_key"].isin(channel_keys)]
    return frame.sort_values("last_touch_revenue", ascending=False).reset_index(drop=True)


def filter_campaign_performance(
    company_ids: list[str] | None = None,
    channel_keys: list[str] | None = None,
) -> pd.DataFrame:
    frame = load_campaign_performance_raw().copy()
    company_ids = _selected(company_ids)
    channel_keys = _selected(channel_keys)

    if company_ids:
        frame = frame[
            frame["target_company_id"].isna()
            | frame["target_company_id"].isin(company_ids)
        ]
    if channel_keys:
        frame = frame[frame["channel_key"].isin(channel_keys)]
    return frame.reset_index(drop=True)


def filter_company_analysis(company_ids: list[str] | None = None) -> pd.DataFrame:
    frame = load_company_analysis_raw().copy()
    company_ids = _selected(company_ids)
    if company_ids:
        frame = frame[frame["company_id"].isin(company_ids)]
    return frame.reset_index(drop=True)


def filter_monthly_revenue(
    company_ids: list[str] | None = None,
    channel_keys: list[str] | None = None,
) -> pd.DataFrame:
    company_ids = _selected(company_ids)
    channel_keys = _selected(channel_keys)

    if not company_ids and not channel_keys:
        return load_monthly_revenue_raw().copy()

    revenue = load_attributed_revenue_raw().copy()
    if company_ids:
        revenue = revenue[revenue["company_id"].isin(company_ids)]
    if channel_keys:
        revenue = revenue[
            revenue["first_touch_channel"].isin(channel_keys)
            | revenue["last_touch_channel"].isin(channel_keys)
        ]

    monthly = (
        revenue.groupby("revenue_month", as_index=False)
        .agg(
            total_revenue=("revenue_amount", "sum"),
            active_customers=("user_id", "nunique"),
        )
        .rename(columns={"revenue_month": "month"})
        .sort_values("month")
        .reset_index(drop=True)
    )
    return monthly


def load_overview_kpis(
    company_ids: list[str] | None = None,
    channel_keys: list[str] | None = None,
) -> dict[str, float | int]:
    company_ids = _selected(company_ids)
    channel_keys = _selected(channel_keys)
    revenue = load_attributed_revenue_raw().copy()

    if company_ids:
        revenue = revenue[revenue["company_id"].isin(company_ids)]
    if channel_keys:
        revenue = revenue[
            revenue["first_touch_channel"].isin(channel_keys)
            | revenue["last_touch_channel"].isin(channel_keys)
        ]

    campaigns = filter_campaign_performance(company_ids, channel_keys)
    channels = filter_channel_performance(company_ids, channel_keys)
    forecast = load_forecast()

    return {
        "total_revenue": float(revenue["revenue_amount"].sum()) if not revenue.empty else 0.0,
        "total_customers": int(revenue["user_id"].nunique()) if not revenue.empty else 0,
        "campaign_count": int(len(campaigns)),
        "channel_count": int(len(channels)),
        "forecast_horizon": int(len(forecast)),
    }


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"
