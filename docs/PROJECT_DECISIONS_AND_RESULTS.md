# Project Decisions & Results

Engineering decisions, implementation approach, challenges, and outcomes for the
Revenue Intelligence Platform take-home.

This document is **documentation only**. It does not change pipeline behavior.

---

## 1. Executive Summary

This project builds an end-to-end **Revenue Intelligence Platform** that connects
marketing touchpoints, campaign metadata, and portfolio revenue into tested,
business-ready analytics. Raw CSV/JSON sources are ingested into a local DuckDB
warehouse, cleaned and attributed in dbt, summarized in an analytics layer, then
extended with short-horizon forecasting, channel anomaly detection, and an
interactive Streamlit dashboard.

The work emphasizes modular, production-style practices: layered transformations,
explicit lineage, revenue conservation checks, dual attribution models, and
separate Python jobs for forecasting and anomalies rather than embedding
everything in a single opaque script.

---

## 2. Key Engineering Approaches

### Layered dbt Architecture

Transformations follow a strict layered design:

```text
Raw
 ↓
Staging
 ↓
Intermediate
 ↓
Marts
 ↓
Analytics
```

This was chosen for:

- **Maintainability** — each layer has a single responsibility
- **Reusability** — marts serve multiple analytics consumers
- **Testing** — contracts and assertions can target the right grain
- **Clear lineage** — raw → clean → attributed → conformed → business summary
- **Production readiness** — mirrors common warehouse modeling standards

### Star Schema

Marts use fact and dimension tables (`fct_*` / `dim_*`) instead of one wide
denormalized table.

Benefits:

- **Query performance** — filter and aggregate on conformed keys
- **BI friendliness** — dimensions are reusable across dashboards and reports
- **Scalability** — new facts can attach to existing dimensions without rewriting
  every summary model

### Attribution Modeling

Both **first-touch** and **last-touch** attribution are implemented in the
intermediate layer and carried through marts and analytics. The Streamlit
**Attribution Comparison** page surfaces channel-level differences so stakeholders
can see how credit shifts by method.

### Data Quality

Quality is enforced at multiple levels:

- dbt generic tests (unique, not-null, relationships, accepted values)
- Custom singular SQL assertions (revenue conservation, non-negative measures)
- Duplicate-key prevention on natural identifiers
- Ingestion validation with results stored in `raw.validation_results`

### Forecasting

Forecasting is a **separate Python package** (`forecasting/`), not a dbt model.
That keeps statistical model fitting, holdout evaluation, and prediction-interval
logic in the right tool (statsmodels/pandas) while dbt remains focused on SQL
transformations.

### Dashboard

The Streamlit app is read-only against `warehouse.duckdb`. It provides:

- Executive KPIs and monthly revenue trends
- Channel, campaign, and company analytics
- First-touch vs last-touch comparison
- 6-month forecast overlay
- Channel anomaly table and trend visualization

### Anomaly Detection

Unusual channel-months are detected with a **rolling z-score** on last-touch
monthly revenue (prior 6-month mean/std). This compares each month to recent
history rather than a single all-time average, which better reflects evolving
baselines.

---

## 3. Major Technical Decisions

### Decision 1 — Layered dbt architecture

**Choice:** Raw → Staging → Intermediate → Marts → Analytics.

**Why:** Separates cleaning from attribution from conformal modeling from
business summaries. Failures and tests localize cleanly; analytics never reads
raw tables.

### Decision 2 — Star schema instead of denormalized tables

**Choice:** Dimensions (`dim_channel`, `dim_company`, `dim_time`,
`dim_user_cohort`) plus facts (`fct_attributed_revenue`, `fct_campaign_roi`,
`fct_content_performance`).

**Why:** Supports consistent joins, reusable descriptors, and BI-friendly
reporting without duplicating company/channel labels across every fact row.

### Decision 3 — Support both first-touch and last-touch attribution

**Choice:** Resolve and store both methods with quality flags.

**Why:** First-touch highlights acquisition channels; last-touch highlights
conversion-proximate channels. Dual models avoid over-committing to a single
credit story and enable side-by-side analytics.

### Decision 4 — Revenue conservation validation across transformations

**Choice:** Singular tests that attributed/analytics totals reconcile to upstream
revenue grain.

**Why:** Attribution must reallocate credit, not invent or drop dollars. Conservation
is the strongest guardrail that marketing metrics remain financially honest.

### Decision 5 — Replace Linear Regression with Holt’s Exponential Smoothing

**Choice:** Final forecast uses Holt (`trend="add"`, no seasonality,
`optimized=True`).

**Why:** The initial Linear Regression baseline forced a single global slope. The
monthly revenue series moves from early growth into a plateau, so linear
extrapolation overshot badly. Holt adapts level and trend over time and cut
holdout error dramatically.

### Decision 6 — Rolling z-score anomalies vs full-history average

**Choice:** Prior 6-month rolling mean/std; flag `|z| ≥ 2.75`.

**Why:** A full-history mean is dominated by early growth and later scale. A short
rolling window detects shocks relative to the recent operating baseline, which is
more actionable for channel monitoring.

### Decision 7 — Schema tests plus business-rule validations

**Choice:** Combine dbt generic tests with custom conservation and non-negativity
assertions, plus pytest for Python pipelines.

**Why:** Schema tests catch structural breakage; business rules catch silent
economic errors that type/uniqueness tests alone miss.

---

## 4. Challenges Encountered

### Forecasting

**Problem:** The first Linear Regression forecast looked “complete” but failed
holdout evaluation (very large MAE/RMSE and deeply negative R²).

**Investigation:** The issue was model assumption mismatch, not broken input data.
Monthly portfolio revenue transitions from rapid growth to a flatter regime; a
single fitted line cannot represent both phases.

**Resolution:** Switch to Holt’s Exponential Smoothing with additive trend and no
seasonality. Holdout error fell by roughly an order of magnitude.

| Metric | Linear Regression | Holt’s |
| --- | ---: | ---: |
| MAE | 92,087.79 | 7,135.00 |
| RMSE | 92,941.76 | 9,478.93 |
| R² | -117.24 | -0.23 |

R² remains slightly negative because the holdout window is short and relatively
flat: even a good trend model can explain less variance than a naive mean on a
nearly level segment. Absolute error (MAE/RMSE) is the more meaningful success
signal here, and Holt wins clearly.

### Anomaly Detection

**Problem:** The first rolling-z implementation flagged too many channel-months,
reducing signal for reviewers.

**Refinements:**

- Exclude the `unknown` channel
- Drop warm-up months before a full 6-month window exists
- Raise thresholds (moderate ≥ 2.75, severe > 3.5)
- Add expected revenue, difference, direction, rank, and plain-English explanations
- Default the dashboard to anomaly-only rows with severity color-coding
- Plot full channel history on the chart (not only anomaly points) so trends remain
  readable

---

## 5. Final Results

### Data Quality

- **17/17** dbt models built successfully
- **259/259** dbt tests passed
- Revenue conservation verified (marts and analytics)
- Duplicate natural keys guarded by uniqueness tests
- Non-negative fact and analytics measures verified

### Analytics Layer

Completed business models:

- `analytics.channel_performance`
- `analytics.campaign_performance`
- `analytics.company_revenue_analysis`
- `analytics.monthly_revenue_customer_growth`

### Forecasting

Final implementation: Holt exponential smoothing, 6-month horizon, holdout metrics
and historical comparison tables in the `forecasting` schema. Materially better
MAE/RMSE than the Linear Regression baseline.

### Dashboard

Streamlit pages deliver:

- Revenue and customer KPIs
- Channel / campaign / company views
- First-touch vs last-touch comparison
- Forecast visualization
- Channel anomaly detection with ranked explanations

### Documentation

- Root `README.md` — setup, architecture, runbook
- `docs/DATA_LINEAGE.md` — end-to-end lineage, Mermaid diagram, dependencies
- `docs/PROJECT_DECISIONS_AND_RESULTS.md` — this decisions/results summary
- Package READMEs for forecasting, anomaly detection, and Streamlit

---

## 6. Key Conclusions

- A **layered dbt architecture** keeps cleaning, attribution, conformal modeling,
  and business summaries separable and testable.
- **Revenue conservation** is essential: attribution may reallocate credit, but
  totals must remain financially consistent.
- **Multiple attribution models** improve insight by showing how channel credit
  changes under different assumptions.
- **Holt’s Exponential Smoothing** outperformed Linear Regression because it
  adapts to a growth-then-plateau series instead of extrapolating one slope.
- **Rolling z-score anomaly detection** is a practical monitor for channel shocks
  relative to recent history, especially after excluding noise (`unknown`, warm-up
  months) and tightening thresholds.
- Combining **dbt schema tests with business-rule assertions and pytest** catches
  both structural and economic failures.
- Together, ingestion, dbt transformations, analytics, forecasting, anomaly
  detection, visualization, and documentation form a complete,
  **production-style Revenue Intelligence Platform** suitable for technical review
  and portfolio demonstration.

---

## Related Documents

- [`docs/DATA_LINEAGE.md`](DATA_LINEAGE.md) — data flow and model dependencies
- [`forecasting/README.md`](../forecasting/README.md) — forecast methodology
- [`anomaly_detection/README.md`](../anomaly_detection/README.md) — anomaly method
- [`streamlit_app/README.md`](../streamlit_app/README.md) — dashboard pages and sources
