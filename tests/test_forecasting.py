"""Tests for the Holt exponential-smoothing forecasting pipeline."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from forecasting.run_forecast import FORECAST_HORIZON_MONTHS, MODEL_NAME, run_forecast

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = PROJECT_ROOT / "warehouse.duckdb"


@pytest.fixture(scope="module")
def forecast_result() -> dict:
    if not WAREHOUSE.is_file():
        pytest.skip("warehouse.duckdb is required for forecasting tests")
    return run_forecast(db_path=WAREHOUSE)


def test_forecast_pipeline_runs(forecast_result: dict) -> None:
    assert forecast_result["forecast_months"] == FORECAST_HORIZON_MONTHS
    assert "mae" in forecast_result["metrics"]
    assert "rmse" in forecast_result["metrics"]
    assert "r2_score" in forecast_result["metrics"]


def test_model_name_is_holt_exponential_smoothing(forecast_result: dict) -> None:
    del forecast_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        model_name = connection.execute(
            "SELECT model_name FROM forecasting.forecast_metrics"
        ).fetchone()[0]
        forecast_model_names = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT model_name FROM forecasting.revenue_forecast"
            ).fetchall()
        }
    assert model_name == MODEL_NAME
    assert forecast_model_names == {MODEL_NAME}


def test_forecast_tables_exist(forecast_result: dict) -> None:
    del forecast_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'forecasting'
                """
            ).fetchall()
        }
    assert {
        "revenue_forecast",
        "forecast_metrics",
        "forecast_comparison",
    } <= tables


def test_exactly_six_future_months_without_nulls(forecast_result: dict) -> None:
    del forecast_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        count, nulls = connection.execute(
            """
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE predicted_revenue IS NULL)
            FROM forecasting.revenue_forecast
            """
        ).fetchone()
        overlap = connection.execute(
            """
            SELECT COUNT(*)
            FROM forecasting.revenue_forecast AS forecast
            INNER JOIN analytics.monthly_revenue_customer_growth AS history
                ON forecast.month = history.month_start_date
            """
        ).fetchone()[0]

    assert count == FORECAST_HORIZON_MONTHS
    assert nulls == 0
    assert overlap == 0


def test_metrics_and_comparison_populated(forecast_result: dict) -> None:
    del forecast_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        metrics_count = connection.execute(
            "SELECT COUNT(*) FROM forecasting.forecast_metrics"
        ).fetchone()[0]
        comparison_count = connection.execute(
            "SELECT COUNT(*) FROM forecasting.forecast_comparison"
        ).fetchone()[0]
        null_predictions = connection.execute(
            """
            SELECT COUNT(*)
            FROM forecasting.forecast_comparison
            WHERE predicted_revenue IS NULL OR prediction_error IS NULL
            """
        ).fetchone()[0]

    assert metrics_count == 1
    assert comparison_count == 18
    assert null_predictions == 0
