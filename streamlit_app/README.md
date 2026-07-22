# Streamlit Dashboard

Read-only dashboard for the Customer Revenue Attribution Pipeline.

## What It Shows

Sidebar pages:

1. **Executive Overview** — KPIs and monthly revenue trend
2. **Channel Performance** — first/last-touch revenue, budget, CTR
3. **Campaign Performance** — ROI, ROAS, revenue, cost per customer
4. **Company Analysis** — revenue, portfolio share, ARPU
5. **Forecast** — historical revenue overlaid with the 6-month forecast
6. **Attribution Comparison** — first-touch vs last-touch channel revenue
7. **Anomaly Detection** — rolling z-score anomalies on monthly channel revenue

All charts use Plotly Express. Filters for company and channel apply across pages
where the underlying warehouse data supports them.

## Data Sources

The app opens `warehouse.duckdb` in read-only mode and queries:

- `analytics.channel_performance`
- `analytics.campaign_performance`
- `analytics.company_revenue_analysis`
- `analytics.monthly_revenue_customer_growth`
- `marts.fct_attributed_revenue`
- `forecasting.revenue_forecast`
- `anomaly.channel_revenue_anomalies`

It does not invent attribution logic or write to the warehouse.

## Prerequisites

Build the warehouse first:

```bash
make ingest
make transform
make forecast
make anomaly
```

## Install

From the repository root:

```bash
source .venv/bin/activate
pip install -r streamlit_app/requirements.txt
```

`pandas` and `duckdb` are already provided by the root `requirements.txt`.

## Launch

```bash
streamlit run streamlit_app/app.py
```

Then open the local URL shown in the terminal (usually `http://localhost:8501`).

## Notes

- Query results are cached with `@st.cache_data`.
- Forecast values remain portfolio-level even when company/channel filters are set;
  historical series still respect those filters where possible.
- No dbt, marts, analytics SQL, or forecasting code is modified by this app.
