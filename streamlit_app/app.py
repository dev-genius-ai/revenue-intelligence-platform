"""Streamlit dashboard for the revenue attribution and forecasting warehouse."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import (
    filter_campaign_performance,
    filter_channel_performance,
    filter_company_analysis,
    filter_monthly_revenue,
    format_currency,
    format_pct,
    get_db_path,
    load_channel_anomalies,
    load_filter_options,
    load_forecast,
    load_overview_kpis,
)

st.set_page_config(
    page_title="Revenue Attribution Dashboard",
    page_icon="📊",
    layout="wide",
)

PAGES = [
    "Executive Overview",
    "Channel Performance",
    "Campaign Performance",
    "Company Analysis",
    "Forecast",
    "Attribution Comparison",
    "Anomaly Detection",
]


def render_sidebar() -> tuple[str, list[str], list[str]]:
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Page", PAGES)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Filters")

    options = load_filter_options()
    company_labels = {
        row.company_id: row.company_name for row in options["companies"].itertuples()
    }
    channel_labels = {
        row.channel_key: row.channel_name for row in options["channels"].itertuples()
    }

    selected_company_names = st.sidebar.multiselect(
        "Company",
        options=list(company_labels.values()),
        default=[],
        help="Leave empty to include all companies.",
    )
    selected_channel_names = st.sidebar.multiselect(
        "Channel",
        options=list(channel_labels.values()),
        default=[],
        help="Leave empty to include all channels.",
    )

    company_ids = [
        company_id
        for company_id, name in company_labels.items()
        if name in selected_company_names
    ]
    channel_keys = [
        channel_key
        for channel_key, name in channel_labels.items()
        if name in selected_channel_names
    ]

    st.sidebar.caption(f"Warehouse: `{get_db_path().name}`")
    return page, company_ids, channel_keys


def page_executive_overview(company_ids: list[str], channel_keys: list[str]) -> None:
    st.header("Executive Overview")
    kpis = load_overview_kpis(company_ids, channel_keys)
    monthly = filter_monthly_revenue(company_ids, channel_keys)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Revenue", format_currency(kpis["total_revenue"]))
    col2.metric("Total Customers", f"{kpis['total_customers']:,}")
    col3.metric("Campaigns", f"{kpis['campaign_count']:,}")
    col4.metric("Channels", f"{kpis['channel_count']:,}")
    col5.metric("Forecast Horizon", f"{kpis['forecast_horizon']} months")

    st.subheader("Monthly Revenue Trend")
    if monthly.empty:
        st.info("No monthly revenue available for the selected filters.")
        return

    fig = px.line(
        monthly,
        x="month",
        y="total_revenue",
        markers=True,
        labels={"month": "Month", "total_revenue": "Revenue"},
        title="Monthly Revenue",
    )
    fig.update_layout(xaxis_title="Month", yaxis_title="Revenue (USD)")
    st.plotly_chart(fig, use_container_width=True)

    if "active_customers" in monthly.columns:
        fig_customers = px.line(
            monthly,
            x="month",
            y="active_customers",
            markers=True,
            labels={"month": "Month", "active_customers": "Active Customers"},
            title="Monthly Active Customers",
        )
        st.plotly_chart(fig_customers, use_container_width=True)


def page_channel_performance(company_ids: list[str], channel_keys: list[str]) -> None:
    st.header("Channel Performance")
    channels = filter_channel_performance(company_ids, channel_keys)
    if channels.empty:
        st.info("No channel performance rows for the selected filters.")
        return

    comparison = channels.melt(
        id_vars=["channel_name"],
        value_vars=["first_touch_revenue", "last_touch_revenue"],
        var_name="attribution_model",
        value_name="revenue",
    )
    comparison["attribution_model"] = comparison["attribution_model"].map(
        {
            "first_touch_revenue": "First Touch",
            "last_touch_revenue": "Last Touch",
        }
    )

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            comparison,
            x="channel_name",
            y="revenue",
            color="attribution_model",
            barmode="group",
            title="Revenue by Channel (First vs Last Touch)",
            labels={"channel_name": "Channel", "revenue": "Revenue"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig_budget = px.bar(
            channels,
            x="channel_name",
            y="campaign_budget_usd",
            title="Campaign Budget by Channel",
            labels={"channel_name": "Channel", "campaign_budget_usd": "Budget"},
        )
        st.plotly_chart(fig_budget, use_container_width=True)

    fig_ctr = px.bar(
        channels.dropna(subset=["click_through_rate"]),
        x="channel_name",
        y="click_through_rate",
        title="Click-Through Rate by Channel",
        labels={"channel_name": "Channel", "click_through_rate": "CTR"},
    )
    st.plotly_chart(fig_ctr, use_container_width=True)

    display = channels.copy()
    display["first_touch_revenue"] = display["first_touch_revenue"].map(format_currency)
    display["last_touch_revenue"] = display["last_touch_revenue"].map(format_currency)
    display["campaign_budget_usd"] = display["campaign_budget_usd"].map(format_currency)
    display["click_through_rate"] = display["click_through_rate"].map(
        lambda value: format_pct(value) if pd.notna(value) else "—"
    )
    st.dataframe(
        display[
            [
                "channel_name",
                "channel_group",
                "first_touch_revenue",
                "last_touch_revenue",
                "campaign_budget_usd",
                "click_through_rate",
                "views",
                "clicks",
                "campaign_count",
            ]
        ],
        use_container_width=True,
    )


def page_campaign_performance(company_ids: list[str], channel_keys: list[str]) -> None:
    st.header("Campaign Performance")
    campaigns = filter_campaign_performance(company_ids, channel_keys)
    if campaigns.empty:
        st.info("No campaigns for the selected filters.")
        return

    sort_by = st.selectbox(
        "Sort by",
        options=[
            "Last-Touch ROI",
            "First-Touch ROI",
            "Last-Touch Revenue",
            "First-Touch Revenue",
            "Budget",
        ],
    )
    sort_map = {
        "Last-Touch ROI": "last_touch_roi",
        "First-Touch ROI": "first_touch_roi",
        "Last-Touch Revenue": "last_touch_attributed_revenue",
        "First-Touch Revenue": "first_touch_attributed_revenue",
        "Budget": "budget_usd",
    }
    campaigns = campaigns.sort_values(sort_map[sort_by], ascending=False)

    top = campaigns.head(15)
    fig = px.bar(
        top,
        x="campaign_id",
        y="last_touch_roi",
        color="channel_name",
        title="Top Campaigns by Last-Touch ROI",
        labels={"campaign_id": "Campaign", "last_touch_roi": "ROI"},
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_roas = px.scatter(
        campaigns,
        x="budget_usd",
        y="last_touch_roas",
        size="last_touch_attributed_revenue",
        color="channel_name",
        hover_name="campaign_id",
        title="Budget vs Last-Touch ROAS",
        labels={"budget_usd": "Budget", "last_touch_roas": "ROAS"},
    )
    st.plotly_chart(fig_roas, use_container_width=True)

    display = campaigns[
        [
            "campaign_id",
            "channel_name",
            "target_company_name",
            "budget_usd",
            "last_touch_attributed_revenue",
            "first_touch_attributed_revenue",
            "last_touch_roi",
            "first_touch_roi",
            "last_touch_roas",
            "first_touch_roas",
            "last_touch_cost_per_customer",
            "first_touch_cost_per_customer",
        ]
    ].copy()
    for column in [
        "budget_usd",
        "last_touch_attributed_revenue",
        "first_touch_attributed_revenue",
        "last_touch_cost_per_customer",
        "first_touch_cost_per_customer",
    ]:
        display[column] = display[column].map(
            lambda value: format_currency(value) if pd.notna(value) else "—"
        )
    st.dataframe(display, use_container_width=True)


def page_company_analysis(company_ids: list[str], channel_keys: list[str]) -> None:
    st.header("Company Analysis")
    del channel_keys  # company page is company-scoped; channel filter is shown in caption
    companies = filter_company_analysis(company_ids)
    if companies.empty:
        st.info("No companies for the selected filters.")
        return

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            companies,
            x="company_name",
            y="total_revenue",
            color="industry",
            title="Revenue by Company",
            labels={"company_name": "Company", "total_revenue": "Revenue"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with right:
        fig_pie = px.pie(
            companies,
            names="company_name",
            values="total_revenue",
            title="Portfolio Revenue Share",
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    fig_arpu = px.bar(
        companies,
        x="company_name",
        y="average_revenue_per_customer",
        title="Average Revenue per Customer",
        labels={
            "company_name": "Company",
            "average_revenue_per_customer": "ARPU",
        },
    )
    st.plotly_chart(fig_arpu, use_container_width=True)

    display = companies.copy()
    display["total_revenue"] = display["total_revenue"].map(format_currency)
    display["average_revenue_per_customer"] = display[
        "average_revenue_per_customer"
    ].map(format_currency)
    display["portfolio_revenue_share"] = display["portfolio_revenue_share"].map(
        format_pct
    )
    st.dataframe(
        display[
            [
                "company_name",
                "industry",
                "total_revenue",
                "customer_count",
                "average_revenue_per_customer",
                "portfolio_revenue_share",
            ]
        ],
        use_container_width=True,
    )


def page_forecast(company_ids: list[str], channel_keys: list[str]) -> None:
    st.header("Revenue Forecast")
    if company_ids or channel_keys:
        st.caption(
            "Forecast values are portfolio-level. Historical trend below respects "
            "the selected company/channel filters where applicable."
        )

    history = filter_monthly_revenue(company_ids, channel_keys)
    forecast = load_forecast()

    history_plot = history[["month", "total_revenue"]].copy()
    history_plot["series"] = "Historical"
    history_plot = history_plot.rename(columns={"total_revenue": "revenue"})

    forecast_plot = forecast[["month", "predicted_revenue"]].copy()
    forecast_plot["series"] = "Forecast"
    forecast_plot = forecast_plot.rename(columns={"predicted_revenue": "revenue"})

    combined = pd.concat([history_plot, forecast_plot], ignore_index=True)
    fig = px.line(
        combined,
        x="month",
        y="revenue",
        color="series",
        markers=True,
        title="Historical Revenue vs 6-Month Forecast",
        labels={"month": "Month", "revenue": "Revenue", "series": "Series"},
    )
    # Distinguish forecast with dashed line
    for trace in fig.data:
        if trace.name == "Forecast":
            trace.line["dash"] = "dash"
    st.plotly_chart(fig, use_container_width=True)

    band = go.Figure()
    if not history.empty:
        band.add_trace(
            go.Scatter(
                x=history["month"],
                y=history["total_revenue"],
                mode="lines+markers",
                name="Historical",
            )
        )
    band.add_trace(
        go.Scatter(
            x=forecast["month"],
            y=forecast["upper_bound"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            name="Upper Bound",
        )
    )
    band.add_trace(
        go.Scatter(
            x=forecast["month"],
            y=forecast["lower_bound"],
            mode="lines",
            fill="tonexty",
            line={"width": 0},
            name="Forecast Interval",
            fillcolor="rgba(255, 127, 14, 0.2)",
        )
    )
    band.add_trace(
        go.Scatter(
            x=forecast["month"],
            y=forecast["predicted_revenue"],
            mode="lines+markers",
            name="Forecast",
            line={"dash": "dash"},
        )
    )
    band.update_layout(
        title="Forecast with Prediction Interval",
        xaxis_title="Month",
        yaxis_title="Revenue (USD)",
    )
    st.plotly_chart(band, use_container_width=True)

    display = forecast.copy()
    for column in ["predicted_revenue", "lower_bound", "upper_bound"]:
        display[column] = display[column].map(format_currency)
    st.subheader("Forecast Table")
    st.dataframe(display, use_container_width=True)


def page_attribution_comparison(
    company_ids: list[str], channel_keys: list[str]
) -> None:
    st.header("Attribution Comparison")
    st.caption(
        "Compares existing first-touch and last-touch revenue already calculated in "
        "the analytics/marts layers. No new attribution logic is applied here."
    )

    channels = filter_channel_performance(company_ids, channel_keys)
    if channels.empty:
        st.info("No attribution data for the selected filters.")
        return

    comparison = channels[
        ["channel_key", "channel_name", "first_touch_revenue", "last_touch_revenue"]
    ].copy()
    comparison["difference"] = (
        comparison["last_touch_revenue"] - comparison["first_touch_revenue"]
    )
    comparison["pct_difference"] = comparison.apply(
        lambda row: (
            (row["difference"] / row["first_touch_revenue"])
            if row["first_touch_revenue"]
            else None
        ),
        axis=1,
    )

    melted = comparison.melt(
        id_vars=["channel_name"],
        value_vars=["first_touch_revenue", "last_touch_revenue"],
        var_name="attribution_model",
        value_name="revenue",
    )
    melted["attribution_model"] = melted["attribution_model"].map(
        {
            "first_touch_revenue": "First Touch",
            "last_touch_revenue": "Last Touch",
        }
    )

    fig = px.bar(
        melted,
        x="channel_name",
        y="revenue",
        color="attribution_model",
        barmode="group",
        title="First-Touch vs Last-Touch Revenue by Channel",
        labels={"channel_name": "Channel", "revenue": "Revenue"},
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_diff = px.bar(
        comparison.sort_values("difference"),
        x="difference",
        y="channel_name",
        orientation="h",
        title="Last-Touch Minus First-Touch Revenue",
        labels={"difference": "Difference", "channel_name": "Channel"},
    )
    st.plotly_chart(fig_diff, use_container_width=True)

    display = comparison.copy()
    display["first_touch_revenue"] = display["first_touch_revenue"].map(format_currency)
    display["last_touch_revenue"] = display["last_touch_revenue"].map(format_currency)
    display["difference"] = display["difference"].map(format_currency)
    display["pct_difference"] = display["pct_difference"].map(
        lambda value: format_pct(value) if pd.notna(value) else "—"
    )
    st.subheader("Comparison Table")
    st.dataframe(
        display[
            [
                "channel_name",
                "first_touch_revenue",
                "last_touch_revenue",
                "difference",
                "pct_difference",
            ]
        ],
        use_container_width=True,
    )


def _severity_row_styles(row: pd.Series) -> list[str]:
    colors = {
        "severe": "background-color: #f5b7b1; color: #7b241c",
        "moderate": "background-color: #f9e79f; color: #7d6608",
        "normal": "background-color: #d5f5e3; color: #196f3d",
    }
    style = colors.get(str(row.get("severity", "")), "")
    return [style] * len(row)


def page_anomaly_detection(channel_keys: list[str]) -> None:
    st.header("Anomaly Detection")
    st.caption(
        "Rolling 6-month z-score on last-touch monthly channel revenue. "
        "Anomaly when |z| ≥ 2.75 (moderate); |z| > 3.5 is severe. "
        "Unknown channel and warm-up months are excluded."
    )

    try:
        anomalies = load_channel_anomalies()
    except Exception as exc:  # noqa: BLE001 — surface missing table to the UI
        st.warning(
            "Anomaly table not found. Run "
            "`python anomaly_detection/run_anomaly_detection.py` first."
        )
        st.caption(str(exc))
        return

    if anomalies.empty:
        st.info("No anomaly rows available.")
        return

    if channel_keys:
        anomalies = anomalies[anomalies["channel"].isin(channel_keys)].copy()

    channel_options = sorted(anomalies["channel_name"].dropna().unique().tolist())
    selected_names = st.multiselect(
        "Highlight channels",
        options=channel_options,
        default=channel_options,
        help="Subset channels for the trend chart and table.",
    )
    if selected_names:
        anomalies = anomalies[anomalies["channel_name"].isin(selected_names)].copy()

    show_all_rows = st.toggle(
        "Show all scored months",
        value=False,
        help="Off by default: show only flagged anomalies.",
    )
    display = anomalies if show_all_rows else anomalies[anomalies["is_anomaly"]].copy()

    anomaly_rows = anomalies[anomalies["is_anomaly"]].copy()
    col1, col2, col3 = st.columns(3)
    col1.metric("Channels", f"{anomalies['channel'].nunique():,}")
    col2.metric("Scored months", f"{anomalies['month_start_date'].nunique():,}")
    col3.metric("Anomalies", f"{len(anomaly_rows):,}")

    st.subheader("Monthly Revenue Trend")
    fig = go.Figure()
    # Always plot full scored history for context. When the table is
    # anomaly-only, limit lines to channels that have at least one anomaly.
    if show_all_rows:
        trend_source = anomalies
    else:
        anomalous_channels = set(anomaly_rows["channel_name"].dropna().tolist())
        trend_source = anomalies[
            anomalies["channel_name"].isin(anomalous_channels)
        ].copy()

    for channel_name, group in trend_source.groupby("channel_name", sort=True):
        group = group.sort_values("month_start_date")
        fig.add_trace(
            go.Scatter(
                x=group["month_start_date"],
                y=group["monthly_revenue"],
                mode="lines+markers",
                name=channel_name,
                hovertemplate=(
                    "%{x|%Y-%m}<br>%{fullData.name}: %{y:$,.0f}<extra></extra>"
                ),
            )
        )
    if not anomaly_rows.empty:
        severity_colors = anomaly_rows["severity"].map(
            {
                "severe": "#c0392b",
                "moderate": "#d4ac0d",
                "normal": "#1e8449",
            }
        )
        fig.add_trace(
            go.Scatter(
                x=anomaly_rows["month_start_date"],
                y=anomaly_rows["monthly_revenue"],
                mode="markers",
                name="Anomaly",
                marker={
                    "size": 12,
                    "symbol": "x",
                    "color": severity_colors,
                    "line": {"width": 1, "color": "#1c2833"},
                },
                hovertemplate=(
                    "Anomaly %{x|%Y-%m}<br>"
                    "%{customdata[0]}<br>"
                    "Revenue: %{y:$,.0f}<br>"
                    "z=%{customdata[1]}<br>"
                    "%{customdata[2]} · %{customdata[3]}<extra></extra>"
                ),
                customdata=anomaly_rows[
                    ["channel_name", "z_score", "severity", "anomaly_direction"]
                ].to_numpy(),
            )
        )
    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Monthly Revenue",
        legend_title="Channel",
        hovermode="closest",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Anomaly Table")
    if display.empty:
        st.info("No anomalies match the current filters.")
        return

    table = display.assign(_abs_z=display["z_score"].abs()).sort_values(
        ["_abs_z", "anomaly_rank"],
        ascending=[False, True],
        na_position="last",
    ).drop(columns="_abs_z")
    table["monthly_revenue"] = table["monthly_revenue"].map(format_currency)
    table["expected_revenue"] = table["expected_revenue"].map(
        lambda value: format_currency(value) if pd.notna(value) else "—"
    )
    table["revenue_difference"] = table["revenue_difference"].map(
        lambda value: format_currency(value) if pd.notna(value) else "—"
    )
    table["rolling_mean"] = table["rolling_mean"].map(
        lambda value: format_currency(value) if pd.notna(value) else "—"
    )
    table["rolling_std"] = table["rolling_std"].map(
        lambda value: f"{value:,.2f}" if pd.notna(value) else "—"
    )
    table["z_score"] = table["z_score"].map(
        lambda value: f"{value:.3f}" if pd.notna(value) else "—"
    )
    table["deviation_percent"] = table["deviation_percent"].map(
        lambda value: f"{value:.1f}%" if pd.notna(value) else "—"
    )
    table["anomaly_rank"] = table["anomaly_rank"].map(
        lambda value: str(int(value)) if pd.notna(value) else "—"
    )
    view = table[
        [
            "anomaly_rank",
            "month_start_date",
            "channel_name",
            "monthly_revenue",
            "expected_revenue",
            "revenue_difference",
            "z_score",
            "deviation_percent",
            "severity",
            "anomaly_direction",
            "explanation",
        ]
    ]
    styled = view.style.apply(_severity_row_styles, axis=1)
    st.dataframe(styled, use_container_width=True)


def main() -> None:
    st.title("Revenue Attribution & Forecasting Dashboard")
    st.write(
        "Read-only views of analytics, marts, and forecasting outputs from "
        "`warehouse.duckdb`."
    )

    page, company_ids, channel_keys = render_sidebar()

    if page == "Executive Overview":
        page_executive_overview(company_ids, channel_keys)
    elif page == "Channel Performance":
        page_channel_performance(company_ids, channel_keys)
    elif page == "Campaign Performance":
        page_campaign_performance(company_ids, channel_keys)
    elif page == "Company Analysis":
        page_company_analysis(company_ids, channel_keys)
    elif page == "Forecast":
        page_forecast(company_ids, channel_keys)
    elif page == "Attribution Comparison":
        page_attribution_comparison(company_ids, channel_keys)
    elif page == "Anomaly Detection":
        page_anomaly_detection(channel_keys)


if __name__ == "__main__":
    main()