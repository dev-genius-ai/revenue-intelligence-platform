# Customer Revenue Attribution Pipeline

## Project Overview

End-to-end Revenue Intelligence Platform that connects marketing touchpoints,
campaign metadata, and portfolio company revenue into tested analytics,
short-horizon forecasting, channel anomaly detection, and an interactive
Streamlit dashboard.

Stack: Python, DuckDB, dbt-duckdb, statsmodels (Holt), pandas rolling z-scores,
Streamlit + Plotly.

## Architecture (summary)

```text
CSV / JSON sources
        │
        ▼
   raw.*  (ingestion)
        │
        ▼
 staging → intermediate → marts → analytics
        │
        ├── forecasting.*
        ├── anomaly.*
        └── Streamlit (read-only)
```

Warehouse: `warehouse.duckdb` at the repo root.

Full schema inventory, Mermaid lineage, and model dependencies:
[`docs/DATA_LINEAGE.md`](docs/DATA_LINEAGE.md).

## Documentation Index

| Document | Contents |
| --- | --- |
| [`docs/DATA_LINEAGE.md`](docs/DATA_LINEAGE.md) | End-to-end lineage, layer explanations, dependencies, validation map |
| [`docs/PROJECT_DECISIONS_AND_RESULTS.md`](docs/PROJECT_DECISIONS_AND_RESULTS.md) | Architecture decisions, trade-offs, challenges, forecast metrics, outcomes |
| [`forecasting/README.md`](forecasting/README.md) | Holt methodology, training data, evaluation, output tables |
| [`anomaly_detection/README.md`](anomaly_detection/README.md) | Rolling z-score method, severity/direction, output schema |
| [`streamlit_app/README.md`](streamlit_app/README.md) | Dashboard pages, filters, data sources, launch notes |
| `dbt_project/models/**/schema.yml` | Model column docs and dbt tests |

## Tech Stack

- Python 3.10+, pandas, DuckDB, PyArrow
- dbt-duckdb for transformations and SQL tests
- statsmodels Holt exponential smoothing for forecasting
- pytest for Python pipelines
- Streamlit + Plotly for the dashboard
- GNU Make for local commands

## Repository Structure

```text
.
├── data/                 # Immutable source CSV/JSON
├── ingestion/            # load_raw.py, validate.py
├── dbt_project/          # staging → intermediate → marts → analytics
├── forecasting/          # Holt 6-month revenue forecast
├── anomaly_detection/    # Rolling z-score channel anomalies
├── streamlit_app/        # Read-only dashboard
├── tests/                # pytest
├── docs/                 # Lineage + decisions documentation
├── Makefile
├── requirements.txt
└── README.md
```

## Data Sources

| File | Role |
| --- | --- |
| `content_performance.csv` | Content views, clicks, channel, UTMs |
| `user_signups.json` | Signups with company, referral, UTM, touchpoints |
| `portfolio_revenue.csv` | Monthly revenue by user and company |
| `campaign_metadata.csv` | Campaign channel, budget, dates, target company |

Sources intentionally include missing/conflicting attribution fields. The raw loader
preserves values without cleaning or attribution.

## Data Validation

`ingestion/validate.py` checks schemas/types, required fields, duplicates, dates,
non-negative measures, and referential integrity. Structural issues are `FAIL`;
expected attribution-quality issues are `WARN`. Results land in
`raw.validation_results`.

Downstream quality: dbt generic + singular tests (including revenue conservation),
plus pytest for forecasting and anomaly detection. Details in
[`docs/DATA_LINEAGE.md`](docs/DATA_LINEAGE.md) §7 and
[`docs/PROJECT_DECISIONS_AND_RESULTS.md`](docs/PROJECT_DECISIONS_AND_RESULTS.md).

## Pipeline Highlights

- **Attribution:** first-touch and last-touch with fallbacks and campaign matching in
  `int_user_journeys` / `int_attributed_revenue` (see lineage + decisions docs).
- **Marts:** star schema facts/dims for reusable analytics.
- **Analytics:** channel, campaign, company, and monthly growth summaries.
- **Forecasting:** Holt exponential smoothing, 6 months ahead — see
  [`forecasting/README.md`](forecasting/README.md).
- **Anomalies:** rolling 6-month z-score on last-touch channel revenue — see
  [`anomaly_detection/README.md`](anomaly_detection/README.md).
- **Dashboard:** read-only Streamlit views — see
  [`streamlit_app/README.md`](streamlit_app/README.md).

## Running Instructions

```bash
source .venv/bin/activate
make install

make ingest
make validate
make transform          # dbt run
cd dbt_project && dbt test --profiles-dir . && cd ..

make forecast
make anomaly
make dashboard          # streamlit run streamlit_app/app.py
```

Or rebuild end-to-end:

```bash
make run                # ingest → validate → dbt → forecast → anomaly
```

Optional paths:

```bash
python ingestion/load_raw.py --db-path /path/to/warehouse.duckdb --data-dir /path/to/data
python ingestion/validate.py --db-path /path/to/warehouse.duckdb
python forecasting/run_forecast.py
python anomaly_detection/run_anomaly_detection.py
```

Dashboard packages (if needed):

```bash
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

### Quick inspect

```sql
SELECT * FROM forecasting.revenue_forecast ORDER BY month;
SELECT * FROM forecasting.forecast_metrics;
SELECT * FROM anomaly.channel_revenue_anomalies
WHERE is_anomaly
ORDER BY ABS(z_score) DESC;
```

## Engineering Decisions

See [`docs/PROJECT_DECISIONS_AND_RESULTS.md`](docs/PROJECT_DECISIONS_AND_RESULTS.md)
for architectural decisions, Holt vs linear regression results, anomaly refinements,
and final outcomes.
