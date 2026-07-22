"""Tests for the rolling z-score channel anomaly detection pipeline."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from anomaly_detection.run_anomaly_detection import (
    ANOMALY_Z_THRESHOLD,
    ROLLING_WINDOW,
    SEVERE_Z_THRESHOLD,
    compute_channel_anomalies,
    run_anomaly_detection,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = PROJECT_ROOT / "warehouse.duckdb"


@pytest.fixture(scope="module")
def anomaly_result() -> dict:
    if not WAREHOUSE.is_file():
        pytest.skip("warehouse.duckdb is required for anomaly detection tests")
    return run_anomaly_detection(db_path=WAREHOUSE)


def test_pipeline_runs_and_prints_summary_fields(anomaly_result: dict) -> None:
    assert anomaly_result["channels_analyzed"] > 0
    assert anomaly_result["months_analyzed"] > 0
    assert anomaly_result["rows_written"] > 0
    assert anomaly_result["anomalies_detected"] >= 0
    # Warm-up months are dropped, so scored rows are fewer than the full panel.
    assert anomaly_result["rows_written"] < (
        anomaly_result["channels_analyzed"] * anomaly_result["months_analyzed"]
    )


def test_output_table_exists_with_new_columns(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'anomaly'
                """
            ).fetchall()
        }
        columns = {
            row[0]
            for row in connection.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'anomaly'
                  AND table_name = 'channel_revenue_anomalies'
                """
            ).fetchall()
        }
    assert "channel_revenue_anomalies" in tables
    assert {
        "expected_revenue",
        "revenue_difference",
        "deviation_percent",
        "anomaly_direction",
        "anomaly_rank",
        "explanation",
    } <= columns


def test_unknown_channel_excluded_and_warmup_hidden(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        unknown_rows = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE lower(channel) = 'unknown'
            """
        ).fetchone()[0]
        incomplete_windows = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE rolling_mean IS NULL
            """
        ).fetchone()[0]
        blank_explanations = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE explanation IS NULL OR explanation = ''
            """
        ).fetchone()[0]
    assert unknown_rows == 0
    assert incomplete_windows == 0
    assert blank_explanations == 0


def test_no_duplicate_channel_month_rows(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        duplicates = connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT month_start_date, channel, COUNT(*) AS row_count
                FROM anomaly.channel_revenue_anomalies
                GROUP BY month_start_date, channel
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
    assert duplicates == 0


def test_null_z_score_only_when_std_missing_or_zero(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        invalid_nulls = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE z_score IS NULL
              AND rolling_std IS NOT NULL
              AND rolling_std <> 0
            """
        ).fetchone()[0]
        invalid_non_nulls = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE z_score IS NOT NULL
              AND (rolling_std IS NULL OR rolling_std = 0)
            """
        ).fetchone()[0]
    assert invalid_nulls == 0
    assert invalid_non_nulls == 0


def test_anomaly_flag_matches_z_threshold(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        mismatches = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE (
                is_anomaly = TRUE
                AND (z_score IS NULL OR ABS(z_score) < {ANOMALY_Z_THRESHOLD})
            )
            OR (
                is_anomaly = FALSE
                AND z_score IS NOT NULL
                AND ABS(z_score) >= {ANOMALY_Z_THRESHOLD}
            )
            """
        ).fetchone()[0]
    assert mismatches == 0


def test_direction_and_rank_consistency(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        direction_mismatches = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE (
                is_anomaly = FALSE AND anomaly_direction <> 'normal'
            )
            OR (
                is_anomaly = TRUE
                AND z_score > 0
                AND anomaly_direction <> 'positive'
            )
            OR (
                is_anomaly = TRUE
                AND z_score < 0
                AND anomaly_direction <> 'negative'
            )
            """
        ).fetchone()[0]
        rank_mismatches = connection.execute(
            """
            SELECT COUNT(*)
            FROM anomaly.channel_revenue_anomalies
            WHERE (is_anomaly = TRUE AND anomaly_rank IS NULL)
               OR (is_anomaly = FALSE AND anomaly_rank IS NOT NULL)
            """
        ).fetchone()[0]
        rank_order_ok = connection.execute(
            """
            SELECT COUNT(*) = 0
            FROM anomaly.channel_revenue_anomalies AS left_row
            INNER JOIN anomaly.channel_revenue_anomalies AS right_row
                ON left_row.anomaly_rank = right_row.anomaly_rank - 1
            WHERE left_row.is_anomaly
              AND right_row.is_anomaly
              AND ABS(left_row.z_score) < ABS(right_row.z_score)
            """
        ).fetchone()[0]
    assert direction_mismatches == 0
    assert rank_mismatches == 0
    assert rank_order_ok


def test_severity_and_direction_labels_are_valid(anomaly_result: dict) -> None:
    del anomaly_result
    with duckdb.connect(str(WAREHOUSE), read_only=True) as connection:
        severities = {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT severity
                FROM anomaly.channel_revenue_anomalies
                """
            ).fetchall()
        }
        directions = {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT anomaly_direction
                FROM anomaly.channel_revenue_anomalies
                """
            ).fetchall()
        }
    assert severities <= {"normal", "moderate", "severe"}
    assert directions <= {"normal", "positive", "negative"}


def test_compute_anomalies_unit_known_spike() -> None:
    months = pd.date_range("2023-01-01", periods=8, freq="MS").date
    revenues = [90.0, 100.0, 95.0, 105.0, 100.0, 98.0, 102.0, 250.0]
    panel = pd.DataFrame(
        {
            "month_start_date": months,
            "channel": ["blog"] * len(months),
            "monthly_revenue": revenues,
        }
    )
    result = compute_channel_anomalies(panel)
    assert ROLLING_WINDOW == 6
    assert ANOMALY_Z_THRESHOLD == 2.75
    assert SEVERE_Z_THRESHOLD == 3.5
    # Warm-up months are hidden; only scored months remain.
    assert len(result) == 2
    assert result["rolling_mean"].notna().all()
    assert "expected_revenue" in result.columns
    assert "revenue_difference" in result.columns
    assert "explanation" in result.columns

    last = result.iloc[-1]
    assert bool(last["is_anomaly"]) is True
    assert abs(float(last["z_score"])) >= ANOMALY_Z_THRESHOLD
    assert last["anomaly_direction"] == "positive"
    assert int(last["anomaly_rank"]) == 1
    assert last["severity"] in {"moderate", "severe"}
    assert last["expected_revenue"] == pytest.approx(float(last["rolling_mean"]))
    assert last["revenue_difference"] == pytest.approx(
        float(last["monthly_revenue"] - last["expected_revenue"])
    )
    assert "above the 6-month average" in last["explanation"]
