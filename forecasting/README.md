# Forecasting Layer

## Why Holt's Exponential Smoothing

The original Linear Regression baseline extrapolated a constant slope and performed
poorly once monthly revenue transitioned from early growth into a plateau. Holt's
Exponential Smoothing (additive trend, no seasonality) was selected because it:

- adapts level and trend over time instead of forcing one global line
- remains simple and explainable for a short 18-month series
- is a standard baseline for trend-capable forecasting without seasonal complexity
- still supports transparent holdout evaluation with MAE, RMSE, and R²

Configuration:

```python
ExponentialSmoothing(
    series,
    trend="add",
    seasonal=None,
).fit(optimized=True)
```

## Training Data

Source table: `analytics.monthly_revenue_customer_growth`

Columns used:

- `month_start_date` → training month
- `total_revenue` → target variable

No raw tables are read. The series is modeled directly at monthly frequency (`MS`).

## Model Assumptions

- Recent level and trend are more informative than distant early-growth months.
- Additive trend is sufficient; seasonal effects are not estimated.
- Residual errors are approximately homoscedastic for interval construction.
- Approximate prediction intervals use residual standard deviation × 1.96 and do not
  widen automatically with forecast horizon.

## Prediction Horizon

The pipeline forecasts the next **6 months** after the latest observed revenue month.
With history ending in June 2024, the default forecast covers July–December 2024.

## Evaluation Approach

- Evaluate on a holdout of the final 3 historical months (trained on the months before).
- Report MAE, RMSE, and R² from that holdout split.
- Retrain the production model on the full historical series.
- Use the production model for the 6-month forward forecast and historical comparison.
- `forecast_metrics.intercept` stores the final Holt level and `slope` stores the final
  Holt trend so the existing metrics schema remains unchanged.

## Output Tables

Written to the DuckDB `forecasting` schema:

| Table | Grain | Purpose |
|-------|-------|---------|
| `revenue_forecast` | one row per future month | predicted revenue and interval bounds |
| `forecast_metrics` | one row per model run | MAE, RMSE, R², level, trend |
| `forecast_comparison` | one row per historical month | actual vs fitted and error |

## Limitations

- Eighteen months is still a thin sample for robust trend estimation.
- No seasonality, campaign shocks, or company-level heterogeneity are modeled.
- Additive-trend smoothing can lag abrupt structural breaks.
- Prediction intervals assume constant residual variance and do not widen with horizon.
- The model forecasts portfolio-level total revenue only, not channel or company splits.

## How to Run

```bash
# from the repository root, with the virtual environment activated
python forecasting/run_forecast.py
# or
make forecast
```

Optional:

```bash
python forecasting/run_forecast.py --db-path /path/to/warehouse.duckdb
```

Inspect results:

```sql
SELECT * FROM forecasting.revenue_forecast ORDER BY month;
SELECT * FROM forecasting.forecast_metrics;
SELECT * FROM forecasting.forecast_comparison ORDER BY month;
```
