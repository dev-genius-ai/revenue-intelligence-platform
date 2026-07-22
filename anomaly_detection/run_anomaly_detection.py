"""Detect channel monthly revenue anomalies with rolling mean/std z-scores.

Reads channel and month dimensions from analytics tables and aggregates monthly
channel revenue from marts.fct_attributed_revenue (last-touch). Writes:

- anomaly.channel_revenue_anomalies
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "warehouse.duckdb"
ROLLING_WINDOW = 6
ANOMALY_Z_THRESHOLD = 2.75
SEVERE_Z_THRESHOLD = 3.5
EXCLUDED_CHANNELS = frozenset({"unknown"})

LOGGER = logging.getLogger("anomaly_detection")


def _load_channel_keys(connection: duckdb.DuckDBPyConnection) -> list[str]:
    frame = connection.execute(
        """
        SELECT channel_key
        FROM analytics.channel_performance
        WHERE lower(channel_key) NOT IN ('unknown')
        ORDER BY channel_key
        """
    ).fetchdf()
    if frame.empty:
        raise ValueError("No channels found in analytics.channel_performance")
    return [
        key
        for key in frame["channel_key"].astype(str).tolist()
        if key.lower() not in EXCLUDED_CHANNELS
    ]


def _load_month_spine(connection: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    months = connection.execute(
        """
        SELECT month_start_date
        FROM analytics.monthly_revenue_customer_growth
        ORDER BY month_start_date
        """
    ).fetchdf()
    if months.empty:
        raise ValueError(
            "No months found in analytics.monthly_revenue_customer_growth"
        )
    months["month_start_date"] = pd.to_datetime(months["month_start_date"]).dt.date
    return months


def _load_monthly_channel_revenue(
    connection: duckdb.DuckDBPyConnection,
) -> pd.DataFrame:
    """Aggregate last-touch attributed revenue by month and channel."""
    revenue = connection.execute(
        """
        SELECT
            dates.month_start_date,
            revenue.last_touch_channel AS channel,
            SUM(revenue.revenue_amount) AS monthly_revenue
        FROM marts.fct_attributed_revenue AS revenue
        INNER JOIN marts.dim_time AS dates
            ON revenue.revenue_date_key = dates.date_key
        WHERE lower(revenue.last_touch_channel) NOT IN ('unknown')
        GROUP BY
            dates.month_start_date,
            revenue.last_touch_channel
        ORDER BY
            revenue.last_touch_channel,
            dates.month_start_date
        """
    ).fetchdf()

    if revenue.empty:
        raise ValueError(
            "No attributed revenue rows found in marts.fct_attributed_revenue"
        )

    revenue["month_start_date"] = pd.to_datetime(revenue["month_start_date"]).dt.date
    revenue["channel"] = revenue["channel"].astype(str)
    revenue["monthly_revenue"] = revenue["monthly_revenue"].astype(float)
    revenue = revenue[~revenue["channel"].str.lower().isin(EXCLUDED_CHANNELS)]
    return revenue


def _build_channel_month_panel(
    months: pd.DataFrame,
    channels: list[str],
    revenue: pd.DataFrame,
) -> pd.DataFrame:
    """Dense month × channel panel with zero-filled missing revenue."""
    panel = (
        months.assign(_key=1)
        .merge(pd.DataFrame({"channel": channels, "_key": 1}), on="_key")
        .drop(columns="_key")
    )
    panel = panel.merge(
        revenue,
        on=["month_start_date", "channel"],
        how="left",
    )
    panel["monthly_revenue"] = panel["monthly_revenue"].fillna(0.0)
    return panel.sort_values(["channel", "month_start_date"]).reset_index(drop=True)


def _severity(z_score: float | None) -> str:
    if z_score is None or pd.isna(z_score):
        return "normal"
    absolute = abs(float(z_score))
    if absolute < ANOMALY_Z_THRESHOLD:
        return "normal"
    if absolute <= SEVERE_Z_THRESHOLD:
        return "moderate"
    return "severe"


def _anomaly_direction(z_score: float | None, is_anomaly: bool) -> str:
    if not is_anomaly or z_score is None or pd.isna(z_score):
        return "normal"
    if float(z_score) > 0:
        return "positive"
    if float(z_score) < 0:
        return "negative"
    return "normal"


def _deviation_percent(revenue: float, mean: float | None) -> float | None:
    if mean is None or pd.isna(mean) or float(mean) == 0.0:
        return None
    return float((revenue - mean) / mean * 100.0)


def _format_money(value: float) -> str:
    return f"${value:,.0f}"


def _channel_label(channel: str) -> str:
    return channel.replace("_", " ").title()


def _explanation(row: pd.Series) -> str:
    channel = _channel_label(str(row["channel"]))
    month = pd.Timestamp(row["month_start_date"]).strftime("%b %Y")
    actual = float(row["monthly_revenue"])
    expected = float(row["expected_revenue"])
    difference = float(row["revenue_difference"])

    if not bool(row["is_anomaly"]):
        return (
            f"{channel} revenue in {month} was close to the 6-month baseline "
            f"(actual {_format_money(actual)} vs expected {_format_money(expected)})."
        )

    direction_word = "above" if row["anomaly_direction"] == "positive" else "below"
    deviation = row["deviation_percent"]
    deviation_text = (
        f"{abs(float(deviation)):.1f}%" if pd.notna(deviation) else "n/a"
    )
    z_score = float(row["z_score"])
    return (
        f"{channel} revenue in {month} was {deviation_text} {direction_word} the "
        f"6-month average (actual {_format_money(actual)} vs expected "
        f"{_format_money(expected)}, difference {_format_money(difference)}). "
        f"This is a {row['severity']} {row['anomaly_direction']} anomaly "
        f"(z={z_score:.2f}, rank {int(row['anomaly_rank'])})."
    )


def compute_channel_anomalies(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute lagged 6-month rolling stats and z-scores per channel.

    Rolling mean/std use the prior six months only (current month excluded).
    A full six-month history is required before a row is scored; incomplete
    warm-up rows are dropped from the output.
    """
    if panel.empty:
        raise ValueError("Cannot compute anomalies on an empty panel")

    frames: list[pd.DataFrame] = []
    for channel, group in panel.groupby("channel", sort=True):
        if str(channel).lower() in EXCLUDED_CHANNELS:
            continue

        series = group.sort_values("month_start_date").copy()
        prior = series["monthly_revenue"].shift(1)
        series["rolling_mean"] = prior.rolling(
            window=ROLLING_WINDOW, min_periods=ROLLING_WINDOW
        ).mean()
        series["rolling_std"] = prior.rolling(
            window=ROLLING_WINDOW, min_periods=ROLLING_WINDOW
        ).std(ddof=0)

        z_scores: list[float | None] = []
        deviation_percents: list[float | None] = []
        for revenue, mean, std in zip(
            series["monthly_revenue"],
            series["rolling_mean"],
            series["rolling_std"],
            strict=True,
        ):
            deviation_percents.append(_deviation_percent(float(revenue), mean))
            if pd.isna(mean) or pd.isna(std):
                z_scores.append(None)
            elif float(std) == 0.0:
                z_scores.append(None)
            else:
                z_scores.append(float((revenue - mean) / std))

        series["z_score"] = pd.Series(z_scores, index=series.index, dtype="float64")
        series["deviation_percent"] = pd.Series(
            deviation_percents, index=series.index, dtype="float64"
        )
        series["is_anomaly"] = series["z_score"].apply(
            lambda value: bool(
                pd.notna(value) and abs(float(value)) >= ANOMALY_Z_THRESHOLD
            )
        )
        series["severity"] = series["z_score"].apply(_severity)
        series["anomaly_direction"] = [
            _anomaly_direction(z_score, bool(is_anomaly))
            for z_score, is_anomaly in zip(
                series["z_score"], series["is_anomaly"], strict=True
            )
        ]
        series["channel"] = channel
        frames.append(series)

    if not frames:
        raise ValueError("No channels available after exclusions")

    result = pd.concat(frames, ignore_index=True)
    # Hide warm-up months before a full rolling window exists.
    result = result[result["rolling_mean"].notna()].copy().reset_index(drop=True)

    result["expected_revenue"] = result["rolling_mean"]
    result["revenue_difference"] = (
        result["monthly_revenue"] - result["expected_revenue"]
    )

    result["anomaly_rank"] = pd.Series(pd.NA, index=result.index, dtype="Int64")
    anomaly_mask = result["is_anomaly"].fillna(False)
    if anomaly_mask.any():
        ranked = (
            result.loc[anomaly_mask, "z_score"]
            .abs()
            .rank(ascending=False, method="first")
            .astype(int)
        )
        result.loc[anomaly_mask, "anomaly_rank"] = ranked

    result["explanation"] = result.apply(_explanation, axis=1)

    return result[
        [
            "month_start_date",
            "channel",
            "monthly_revenue",
            "expected_revenue",
            "revenue_difference",
            "rolling_mean",
            "rolling_std",
            "z_score",
            "deviation_percent",
            "is_anomaly",
            "severity",
            "anomaly_direction",
            "anomaly_rank",
            "explanation",
        ]
    ].sort_values(["channel", "month_start_date"]).reset_index(drop=True)


def _write_results(
    connection: duckdb.DuckDBPyConnection,
    anomalies: pd.DataFrame,
) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS anomaly")
    connection.execute("DROP TABLE IF EXISTS anomaly.channel_revenue_anomalies")
    connection.execute(
        """
        CREATE TABLE anomaly.channel_revenue_anomalies (
            month_start_date DATE,
            channel VARCHAR,
            monthly_revenue DOUBLE,
            expected_revenue DOUBLE,
            revenue_difference DOUBLE,
            rolling_mean DOUBLE,
            rolling_std DOUBLE,
            z_score DOUBLE,
            deviation_percent DOUBLE,
            is_anomaly BOOLEAN,
            severity VARCHAR,
            anomaly_direction VARCHAR,
            anomaly_rank INTEGER,
            explanation VARCHAR
        )
        """
    )
    connection.register("anomalies_df", anomalies)
    connection.execute(
        """
        INSERT INTO anomaly.channel_revenue_anomalies
        SELECT
            CAST(month_start_date AS DATE),
            channel,
            monthly_revenue,
            expected_revenue,
            revenue_difference,
            rolling_mean,
            rolling_std,
            z_score,
            deviation_percent,
            is_anomaly,
            severity,
            anomaly_direction,
            anomaly_rank,
            explanation
        FROM anomalies_df
        """
    )


def run_anomaly_detection(db_path: Path | str = DEFAULT_DB_PATH) -> dict[str, object]:
    """Execute the anomaly detection pipeline against the local DuckDB warehouse."""
    database_path = Path(db_path).expanduser().resolve()
    if not database_path.is_file():
        raise FileNotFoundError(f"DuckDB warehouse not found: {database_path}")

    LOGGER.info("Reading analytics and marts inputs from %s", database_path)
    connection = duckdb.connect(str(database_path))
    try:
        channels = _load_channel_keys(connection)
        months = _load_month_spine(connection)
        revenue = _load_monthly_channel_revenue(connection)
        panel = _build_channel_month_panel(months, channels, revenue)
        anomalies = compute_channel_anomalies(panel)
        _write_results(connection, anomalies)

        anomaly_count = int(anomalies["is_anomaly"].sum())
        summary = {
            "channels_analyzed": len(channels),
            "months_analyzed": int(months["month_start_date"].nunique()),
            "rows_written": len(anomalies),
            "anomalies_detected": anomaly_count,
        }
        LOGGER.info(
            "Wrote anomaly.channel_revenue_anomalies (%s rows, %s anomalies)",
            summary["rows_written"],
            summary["anomalies_detected"],
        )
    finally:
        connection.close()

    return summary


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
    summary = run_anomaly_detection(db_path=args.db_path)
    print(f"Channels analyzed: {summary['channels_analyzed']}")
    print(f"Months analyzed: {summary['months_analyzed']}")
    print(f"Anomalies detected: {summary['anomalies_detected']}")


if __name__ == "__main__":
    main()
