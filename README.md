# Customer Revenue Attribution Pipeline

## Project Overview

This project will implement an end-to-end analytics pipeline that connects content
performance and customer acquisition data to revenue generated across a portfolio of
companies. The completed pipeline will provide tested attribution models, campaign and
channel analytics, and short-term revenue forecasts.

The repository is being developed incrementally. The project foundation and local raw
ingestion layer are complete; transformation, attribution, analytics, and forecasting
will be added in later phases.

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
└── raw
    ├── campaign_metadata
    ├── content_performance
    ├── portfolio_revenue
    ├── user_signups
    └── validation_results
```

The database location can be changed with `--db-path`. The source directory can be
changed with `--data-dir`.

## Tech Stack

- Python 3.10+
- pandas for tabular data processing
- DuckDB as the local analytical warehouse
- PyArrow for columnar data interchange
- dbt-duckdb for SQL transformations, modeling, and tests
- pytest for Python testing
- GNU Make for repeatable developer commands

## Repository Structure

```text
.
├── data/
│   ├── raw/             # Immutable source data
│   └── processed/       # Generated intermediate data
├── ingestion/           # Raw ingestion and validation code
├── dbt_project/         # Future dbt configuration, models, and tests
├── analytics/           # Future analytical SQL and execution utilities
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
3. **dbt transformations** — build staging, intermediate, dimensional, and fact models
   with automated tests.
4. **Revenue attribution** — implement and compare last-touch and first-touch models.
5. **Analytics** — answer the required channel, campaign, CAC, cohort, and revenue-trend
   questions.
6. **Forecasting** — generate transparent three-month forecasts by company and channel.
7. **Documentation and verification** — publish assumptions, limitations, lineage,
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

## Attribution Approach

The completed pipeline will compare two single-touch attribution methods:

- **Last-touch attribution** assigns revenue credit to the final recorded acquisition
  touchpoint.
- **First-touch attribution** assigns revenue credit to the earliest recorded acquisition
  touchpoint.

The exact channel normalization, fallback rules, conflict handling, and revenue
conservation tests will be defined during the attribution phase.

## Forecasting Approach

The completed pipeline will provide a three-month revenue forecast for each portfolio
company. The baseline method, assumptions, failure modes, and evaluation approach will be
documented when forecasting is implemented.

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

The following command names are reserved for later phases and currently print placeholder
messages:

```bash
make transform
make analytics
make run
```
