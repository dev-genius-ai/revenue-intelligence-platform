# Customer Revenue Attribution Pipeline

## Project Overview

This project will implement an end-to-end analytics pipeline that connects content
performance and customer acquisition data to revenue generated across a portfolio of
companies. The completed pipeline will provide tested attribution models, campaign and
channel analytics, and short-term revenue forecasts.

The repository is being developed incrementally. This phase establishes the project
foundation only; ingestion, transformation, attribution, analytics, and forecasting logic
will be added in later phases.

## Architecture

Architecture diagram and end-to-end data flow will be added when the pipeline components
are implemented.

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
├── ingestion/           # Future ingestion and validation code
├── dbt_project/         # Future dbt configuration, models, and tests
├── analytics/           # Future analytical SQL and execution utilities
├── outputs/             # Generated reports and query results
├── notebooks/           # Optional exploratory analysis
├── tests/               # Future Python tests
├── README.md
├── requirements.txt
├── Makefile
└── .gitignore
```

Empty directories contain `.gitkeep` files so the intended structure is retained in Git.
The starter assessment files currently remain unchanged in `data/`.

## Implementation Roadmap

1. **Project foundation** — repository structure, dependencies, tooling, and
   documentation skeleton.
2. **Ingestion and validation** — idempotently load each source into DuckDB and report
   structural and data-quality issues.
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

These files include intentionally missing or conflicting attribution values. Validation
and resolution rules will be documented when the ingestion and modeling phases are
implemented.

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

Detailed setup and execution instructions will be added as each phase becomes available.
The repository currently exposes the following command interface:

```bash
make install
make ingest
make validate
make transform
make analytics
make run
```

Only `make install` is operational during the foundation phase. The remaining commands
print placeholder messages until their corresponding pipeline phases are implemented.
