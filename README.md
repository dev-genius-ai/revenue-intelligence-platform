# Customer Revenue Attribution Pipeline

## Project Overview

This project will implement an end-to-end analytics pipeline that connects content
performance and customer acquisition data to revenue generated across a portfolio of
companies. The completed pipeline will provide tested attribution models, campaign and
channel analytics, and short-term revenue forecasts.

The repository is being developed incrementally. The project foundation, local raw
ingestion layer, dbt staging layer, intermediate attribution engine, star schema
marts, analytics layer, and Holt exponential-smoothing forecasting pipeline are complete.

## Architecture

The current ingestion layer reads the four immutable starter files from `data/` and
recreates explicitly typed tables in the `raw` schema of a local `warehouse.duckdb`
database. Loading occurs in a single transaction, so a failed run rolls back without
leaving partially replaced tables.

```text
CSV and JSON source files
          │
          ▼
 ingestion/load_raw.py
          │
          ▼
warehouse.duckdb
├── raw
│   ├── campaign_metadata
│   ├── content_performance
│   ├── portfolio_revenue
│   ├── user_signups
│   └── validation_results
├── staging
│   ├── stg_campaign_metadata
│   ├── stg_content_performance
│   ├── stg_portfolio_revenue
│   └── stg_user_signups
├── intermediate
│   ├── int_user_journeys
│   └── int_attributed_revenue
├── marts
│   ├── dim_channel
│   ├── dim_company
│   ├── dim_time
│   ├── dim_user_cohort
│   ├── fct_attributed_revenue
│   ├── fct_campaign_roi
│   └── fct_content_performance
├── analytics
│   ├── channel_performance
│   ├── campaign_performance
│   ├── company_revenue_analysis
│   └── monthly_revenue_customer_growth
└── forecasting
    ├── revenue_forecast
    ├── forecast_metrics
    └── forecast_comparison
```

The database location can be changed with `--db-path`. The source directory can be
changed with `--data-dir`. dbt reads only from `raw` and materializes cleaned tables in
`staging`; attribution models are materialized in `intermediate`, conformed facts and
dimensions in `marts`, and business summaries in `analytics`. The forecasting pipeline
reads analytics monthly totals and writes predictions to the `forecasting` schema.

## Tech Stack

- Python 3.10+
- pandas for tabular data processing
- DuckDB as the local analytical warehouse
- PyArrow for columnar data interchange
- dbt-duckdb for SQL transformations, modeling, and tests
- statsmodels Holt exponential smoothing for revenue forecasting
- pytest for Python testing
- GNU Make for repeatable developer commands

## Repository Structure

```text
.
├── data/
│   ├── raw/             # Immutable source data
│   └── processed/       # Generated intermediate data
├── ingestion/           # Raw ingestion and validation code
├── forecasting/         # Holt exponential-smoothing revenue forecasting pipeline
├── dbt_project/         # dbt staging, intermediate, marts, and analytics models
├── analytics/           # Reserved for ad-hoc SQL notebooks/utilities
├── outputs/             # Generated reports and query results
├── notebooks/           # Optional exploratory analysis
├── tests/               # Python tests
├── README.md
├── requirements.txt
├── Makefile
└── .gitignore
```

Empty directories contain `.gitkeep` files so the intended structure is retained in Git.
The starter assessment files currently remain unchanged in `data/`.

## Implementation Roadmap

1. **Completed: Project foundation** — repository structure, dependencies, tooling, and
   documentation skeleton.
2. **Completed: Ingestion and validation** — idempotently load each source into DuckDB
   and report structural and data-quality issues.
3. **Completed: dbt staging foundation** — clean and type raw sources, document models,
   and enforce generic schema and relationship tests.
4. **Completed: Journey stitching and attribution** — resolve first-touch and
   last-touch channels, validate campaigns, and enrich source-grain revenue.
5. **Completed: Star schema marts** — publish conformed dimensions and tested revenue,
   campaign ROI, and content performance facts.
6. **Completed: Analytics layer** — channel, campaign, company, and monthly growth
   summaries built exclusively from marts.
7. **Completed: Forecasting** — Holt exponential-smoothing 6-month portfolio revenue
   forecast with evaluation metrics and historical comparison.
8. **Documentation and verification** — publish assumptions, limitations, lineage,
   sample outputs, and reproducible setup instructions.

## Data Sources

The assessment provides four deterministic source datasets:

- `content_performance.csv` — content-level views, clicks, channel, and UTM values.
- `user_signups.json` — signup events with company, referral, UTM, and touchpoint data.
- `portfolio_revenue.csv` — monthly revenue records by user and company.
- `campaign_metadata.csv` — campaign channel, budget, date range, and target company.

These files include intentionally missing or conflicting attribution values. The raw
loader preserves source values without applying cleaning or attribution rules.

## Data Validation

`ingestion/validate.py` checks required schemas and DuckDB types, required values,
duplicate primary keys, date formats, non-negative measures, and referential integrity.
It also measures missing UTM/channel values and conflicting attribution fields.

Structural, numeric, date, and referential-integrity problems are reported as `FAIL`.
Expected attribution-quality problems are reported as `WARN` and do not cause ingestion
to fail. Every result is appended to `raw.validation_results` with its check name,
status, message, and UTC timestamp.

## dbt Staging Layer

The dbt project in `dbt_project/` connects to the existing repository-level
`warehouse.duckdb`. Its four staging models retain their source grain and perform only
source-conforming cleanup:

- `stg_campaign_metadata` standardizes identifiers and channels, types campaign dates
  and budgets, and derives a normalized campaign slug.
- `stg_content_performance` standardizes channels and UTM values, types dates and
  engagement metrics, and adds the publication month.
- `stg_portfolio_revenue` standardizes identifiers, converts `month` to a DATE, and
  retains one row per source revenue event.
- `stg_user_signups` standardizes identifiers, signup dates, referral/UTM values, and
  first/last-touch channel values while preserving missing values and conflicts.

No attribution decisions, journey stitching, revenue allocation, or aggregate analytics
occur in staging. Model and source documentation is maintained in
`dbt_project/models/schema.yml`. Tests cover primary-key uniqueness and completeness,
accepted channel/company values, and campaign/user relationships.

## Attribution Approach

`int_user_journeys` produces one row per signup and resolves two independent
single-touch attribution paths:

- **First-touch attribution:** use `first_touch_channel`, then `utm_source`, then
  `referral_source`, and finally `unknown`.
- **Last-touch attribution:** use `last_touch_channel`, then `utm_source`, then
  `referral_source`, and finally `unknown`.

Each path records the resolved channel and the field that supplied it. The model also
flags first-touch versus last-touch conflicts, missing UTM components, campaign match
outcomes, and overall attribution confidence.

Campaigns are assigned independently to each path only when all of these conditions pass:

1. The normalized signup UTM campaign equals the campaign slug.
2. The signup date falls within the inclusive campaign date range.
3. The signup company equals the target company, or the campaign has no target and is
   portfolio-wide.
4. The campaign channel equals that path's resolved channel.

Failed validation leaves the corresponding campaign identifier null.
`int_attributed_revenue` then left joins journeys to revenue without allocating or
aggregating amounts, preserving exactly one row per `revenue_id`.

### Known Attribution Limitations

- The source contains only first-touch and last-touch labels, not a complete ordered
  sequence of customer interactions.
- Attribution fallbacks depend on source-provided fields and cannot recover missing
  touchpoints.
- Campaign matching uses normalized UTM campaign names rather than a direct campaign ID.
- Content IDs are not present in signup records, so this phase cannot attribute revenue
  to an individual content item.
- The confidence label is a deterministic data-quality indicator, not a statistical
  probability or causal estimate.

## Star Schema Marts

The `marts` schema exposes three facts at explicit business grains:

- `fct_attributed_revenue`: one row per `revenue_id`, with first-touch and last-touch
  channel and campaign keys. Revenue values are copied unchanged from the intermediate
  layer.
- `fct_campaign_roi`: one row per `campaign_id`, with budget, attributed revenue,
  customer counts, ROAS, and ROI calculated separately for both attribution methods.
- `fct_content_performance`: one row per publication month, channel, and validated
  campaign combination, with content count, views, clicks, and click-through rate.

Four conformed dimensions provide descriptive context:

- `dim_channel`: normalized channel labels and channel groups.
- `dim_company`: portfolio company names and industries.
- `dim_time`: a daily date spine covering all staged source dates.
- `dim_user_cohort`: one row per signup-month cohort.

Facts retain business identifiers and foreign keys rather than repeating descriptive
labels. dbt relationships enforce fact-to-dimension integrity. Singular tests confirm
that fact measures are non-negative and that `fct_attributed_revenue` preserves both the
record count and total revenue from `int_attributed_revenue`.

## Forecasting Approach

The forecasting pipeline in `forecasting/run_forecast.py` predicts the next **6 months**
of portfolio revenue using Holt's Exponential Smoothing from statsmodels
(`trend="add"`, no seasonality, `optimized=True`).

Why Holt's method:

- It adapts level and trend over time instead of fitting one global linear slope.
- It remains simple and explainable for a short 18-month series.
- It better handles the growth-then-plateau pattern observed in monthly revenue.

Training data comes only from `analytics.monthly_revenue_customer_growth` (never raw).
Holdout MAE/RMSE/R² are computed on the final 3 historical months; the production model
is then refit on the full series. Existing metrics columns `intercept` and `slope` store
the final Holt level and trend for schema compatibility.

Outputs written to DuckDB:

- `forecasting.revenue_forecast` — future month, prediction, lower/upper bound
- `forecasting.forecast_metrics` — MAE, RMSE, R², level, trend
- `forecasting.forecast_comparison` — historical actual vs fitted and error

Limitations: no seasonality or campaign shocks, constant residual variance intervals,
portfolio-level only, and additive-trend smoothing can lag abrupt structural breaks.
See [`forecasting/README.md`](forecasting/README.md) for full methodology detail.

## Running Instructions

Install dependencies and build the local raw layer from the repository root:

```bash
make install
make ingest
make validate
```

The equivalent direct commands are:

```bash
python ingestion/load_raw.py
python ingestion/validate.py
```

Use a different database or source directory when needed:

```bash
python ingestion/load_raw.py --db-path /path/to/warehouse.duckdb --data-dir /path/to/data
python ingestion/validate.py --db-path /path/to/warehouse.duckdb
```

After ingestion, run dbt locally:

```bash
cd dbt_project
dbt debug --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

From the repository root, `make transform` runs all dbt models using the same local
profile. Activate the project virtual environment first so `dbt` is available.

Generate the revenue forecast after analytics models exist:

```bash
make forecast
# or
python forecasting/run_forecast.py
```

Inspect forecast outputs:

```sql
SELECT * FROM forecasting.revenue_forecast ORDER BY month;
SELECT * FROM forecasting.forecast_metrics;
SELECT * FROM forecasting.forecast_comparison ORDER BY month;
```

End-to-end local rebuild:

```bash
make run
```
