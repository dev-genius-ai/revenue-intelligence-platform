"""Train a Holt exponential-smoothing revenue forecast and write results to DuckDB.

Reads monthly revenue from analytics.monthly_revenue_customer_growth, fits a
statsmodels ExponentialSmoothing model with additive trend and no seasonality,
evaluates holdout metrics, and writes:

- forecasting.revenue_forecast
- forecasting.forecast_metrics
- forecasting.forecast_comparison
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.holtwinters import HoltWintersResults

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "warehouse.duckdb"
MODEL_NAME = "holt_exponential_smoothing"
FORECAST_HORIZON_MONTHS = 6
HOLDOUT_MONTHS = 3
CONFIDENCE_Z = 1.96

LOGGER = logging.getLogger("forecasting")


def _load_monthly_history(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    history = connection.execute(
        """
        SELECT
            month_start_date AS month,
            total_revenue AS actual_revenue
        FROM analytics.monthly_revenue_customer_growth
        ORDER BY month_start_date
        """
    ).fetchdf()

    if history.empty:
        raise ValueError(
            "No monthly revenue history found in "
            "analytics.monthly_revenue_customer_growth"
        )

    history["month"] = pd.to_datetime(history["month"]).dt.to_period("M").dt.to_timestamp()
    history = history.sort_values("month").reset_index(drop=True)
    return history


def _to_series(history: pd.DataFrame) -> pd.Series:
    series = history.set_index("month")["actual_revenue"].astype(float)
    series.index.freq = "MS"
    return series


def _fit_holt(series: pd.Series) -> HoltWintersResults:
    """Fit Holt's linear trend method: additive trend, no seasonality."""
    return ExponentialSmoothing(
        series,
        trend="add",
        seasonal=None,
    ).fit(optimized=True)


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    residuals = actual - predicted
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
    return {
        "mae": float(np.mean(np.abs(residuals))),
        "rmse": float(np.sqrt(np.mean(residuals**2))),
        "r2_score": float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else float("nan"),
    }


def _evaluate_holdout(history: pd.DataFrame) -> dict[str, float]:
    """Score a train/holdout split without affecting the final production model."""
    train = history.iloc[:-HOLDOUT_MONTHS].copy()
    holdout = history.iloc[-HOLDOUT_MONTHS:].copy()

    evaluation_model = _fit_holt(_to_series(train))
    holdout_predictions = np.asarray(
        evaluation_model.forecast(HOLDOUT_MONTHS), dtype=float
    )
    actual = holdout["actual_revenue"].to_numpy(dtype=float)

    return {
        **_regression_metrics(actual, holdout_predictions),
        "train_months": float(len(train)),
        "holdout_months": float(len(holdout)),
    }


def _fit_production_model(
    history: pd.DataFrame,
) -> tuple[HoltWintersResults, float, dict[str, float]]:
    if len(history) <= HOLDOUT_MONTHS + 2:
        raise ValueError(
            f"Need more than {HOLDOUT_MONTHS + 2} historical months to train and evaluate"
        )

    holdout_metrics = _evaluate_holdout(history)

    model = _fit_holt(_to_series(history))
    fitted = np.asarray(model.fittedvalues, dtype=float)
    actual = history["actual_revenue"].to_numpy(dtype=float)
    residuals = actual - fitted
    residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0

    # Preserve existing metrics-table columns: map Holt level/trend into intercept/slope.
    level = float(model.params.get("initial_level", fitted[-1]))
    trend = float(model.params.get("initial_trend", 0.0))
    if hasattr(model, "level") and len(model.level) > 0:
        level = float(model.level.iloc[-1])
    if hasattr(model, "trend") and model.trend is not None and len(model.trend) > 0:
        trend = float(model.trend.iloc[-1])

    metrics = {
        **holdout_metrics,
        "residual_std": residual_std,
        "intercept": level,
        "slope": trend,
    }
    return model, residual_std, metrics


def _build_forecast(
    history: pd.DataFrame,
    model: HoltWintersResults,
    residual_std: float,
    generated_at: datetime,
) -> pd.DataFrame:
    last_month = history["month"].iloc[-1]
    future_predictions = np.asarray(
        model.forecast(FORECAST_HORIZON_MONTHS), dtype=float
    )

    rows = []
    for step, predicted in enumerate(future_predictions, start=1):
        future_month = (last_month + pd.DateOffset(months=step)).to_period("M").to_timestamp()
        margin = CONFIDENCE_Z * residual_std
        rows.append(
            {
                "month": future_month.date(),
                "predicted_revenue": round(float(predicted), 2),
                "lower_bound": round(float(predicted) - margin, 2),
                "upper_bound": round(float(predicted) + margin, 2),
                "model_name": MODEL_NAME,
                "generated_at": generated_at,
            }
        )

    forecast = pd.DataFrame(rows)
    if forecast["predicted_revenue"].isna().any():
        raise ValueError("Forecast produced NULL predicted_revenue values")
    if len(forecast) != FORECAST_HORIZON_MONTHS:
        raise ValueError(
            f"Expected {FORECAST_HORIZON_MONTHS} forecast months, got {len(forecast)}"
        )
    return forecast


def _build_comparison(
    history: pd.DataFrame,
    model: HoltWintersResults,
) -> pd.DataFrame:
    predictions = np.asarray(model.fittedvalues, dtype=float)
    comparison = history[["month", "actual_revenue"]].copy()
    comparison["month"] = comparison["month"].dt.date
    comparison["predicted_revenue"] = np.round(predictions, 2)
    comparison["prediction_error"] = np.round(
        comparison["actual_revenue"] - comparison["predicted_revenue"], 2
    )
    return comparison


def _write_results(
    connection: duckdb.DuckDBPyConnection,
    forecast: pd.DataFrame,
    metrics: dict[str, float],
    comparison: pd.DataFrame,
    generated_at: datetime,
) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS forecasting")

    connection.execute("DROP TABLE IF EXISTS forecasting.revenue_forecast")
    connection.execute(
        """
        CREATE TABLE forecasting.revenue_forecast (
            month DATE,
            predicted_revenue DOUBLE,
            lower_bound DOUBLE,
            upper_bound DOUBLE,
            model_name VARCHAR,
            generated_at TIMESTAMPTZ
        )
        """
    )
    connection.register("forecast_df", forecast)
    connection.execute(
        """
        INSERT INTO forecasting.revenue_forecast
        SELECT
            CAST(month AS DATE),
            predicted_revenue,
            lower_bound,
            upper_bound,
            model_name,
            CAST(generated_at AS TIMESTAMPTZ)
        FROM forecast_df
        """
    )

    metrics_frame = pd.DataFrame(
        [
            {
                "model_name": MODEL_NAME,
                "mae": round(metrics["mae"], 4),
                "rmse": round(metrics["rmse"], 4),
                "r2_score": round(metrics["r2_score"], 6),
                "train_months": int(metrics["train_months"]),
                "holdout_months": int(metrics["holdout_months"]),
                "residual_std": round(metrics["residual_std"], 4),
                "intercept": round(metrics["intercept"], 4),
                "slope": round(metrics["slope"], 4),
                "generated_at": generated_at,
            }
        ]
    )
    connection.execute("DROP TABLE IF EXISTS forecasting.forecast_metrics")
    connection.execute(
        """
        CREATE TABLE forecasting.forecast_metrics (
            model_name VARCHAR,
            mae DOUBLE,
            rmse DOUBLE,
            r2_score DOUBLE,
            train_months INTEGER,
            holdout_months INTEGER,
            residual_std DOUBLE,
            intercept DOUBLE,
            slope DOUBLE,
            generated_at TIMESTAMPTZ
        )
        """
    )
    connection.register("metrics_df", metrics_frame)
    connection.execute(
        """
        INSERT INTO forecasting.forecast_metrics
        SELECT
            model_name,
            mae,
            rmse,
            r2_score,
            train_months,
            holdout_months,
            residual_std,
            intercept,
            slope,
            CAST(generated_at AS TIMESTAMPTZ)
        FROM metrics_df
        """
    )

    connection.execute("DROP TABLE IF EXISTS forecasting.forecast_comparison")
    connection.execute(
        """
        CREATE TABLE forecasting.forecast_comparison (
            month DATE,
            actual_revenue DOUBLE,
            predicted_revenue DOUBLE,
            prediction_error DOUBLE
        )
        """
    )
    connection.register("comparison_df", comparison)
    connection.execute(
        """
        INSERT INTO forecasting.forecast_comparison
        SELECT
            CAST(month AS DATE),
            actual_revenue,
            predicted_revenue,
            prediction_error
        FROM comparison_df
        """
    )


def run_forecast(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, object]:
    """Execute the full forecasting pipeline against the local DuckDB warehouse."""
    database_path = Path(db_path).expanduser().resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f"DuckDB warehouse not found: {database_path}")

    generated_at = datetime.now(timezone.utc)
    LOGGER.info("Reading monthly revenue history from %s", database_path)

    connection = duckdb.connect(str(database_path))
    try:
        history = _load_monthly_history(connection)
        LOGGER.info(
            "Loaded %s historical months (%s → %s)",
            len(history),
            history["month"].iloc[0].date(),
            history["month"].iloc[-1].date(),
        )

        model, residual_std, metrics = _fit_production_model(history)
        LOGGER.info(
            "Trained %s on full history | level=%.2f trend=%.2f | "
            "holdout MAE=%.2f RMSE=%.2f R2=%.4f",
            MODEL_NAME,
            metrics["intercept"],
            metrics["slope"],
            metrics["mae"],
            metrics["rmse"],
            metrics["r2_score"],
        )

        forecast = _build_forecast(history, model, residual_std, generated_at)
        comparison = _build_comparison(history, model)
        _write_results(connection, forecast, metrics, comparison, generated_at)

        LOGGER.info(
            "Wrote forecasting.revenue_forecast (%s rows), "
            "forecasting.forecast_metrics, forecasting.forecast_comparison (%s rows)",
            len(forecast),
            len(comparison),
        )
    finally:
        connection.close()

    return {
        "forecast_months": FORECAST_HORIZON_MONTHS,
        "metrics": metrics,
        "generated_at": generated_at.isoformat(),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"DuckDB warehouse path (default: {DEFAULT_DB_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    result = run_forecast(db_path=args.db_path)
    print(
        "Forecasting complete: "
        f"{result['forecast_months']} months | "
        f"MAE={result['metrics']['mae']:.2f} | "
        f"RMSE={result['metrics']['rmse']:.2f} | "
        f"R2={result['metrics']['r2_score']:.4f}"
    )


if __name__ == "__main__":
    main()
