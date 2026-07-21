"""Load the assessment source files into the DuckDB raw schema."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = PROJECT_ROOT / "warehouse.duckdb"

SOURCE_FILES = {
    "campaign_metadata": "campaign_metadata.csv",
    "content_performance": "content_performance.csv",
    "portfolio_revenue": "portfolio_revenue.csv",
    "user_signups": "user_signups.json",
}

LOGGER = logging.getLogger("raw_ingestion")


def _sql_path(path: Path) -> str:
    """Return a safely quoted SQL string literal for a local path."""
    return "'" + str(path.resolve()).replace("'", "''") + "'"


def _require_source_files(data_dir: Path) -> dict[str, Path]:
    paths = {table: data_dir / filename for table, filename in SOURCE_FILES.items()}
    missing = [path for path in paths.values() if not path.is_file()]
    if missing:
        missing_list = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing required source file(s): {missing_list}")
    return paths


def _load_campaign_metadata(
    connection: duckdb.DuckDBPyConnection, source_path: Path
) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE raw.campaign_metadata (
            campaign_id VARCHAR,
            campaign_name VARCHAR,
            channel VARCHAR,
            budget_usd DECIMAL(18, 2),
            start_date VARCHAR,
            end_date VARCHAR,
            target_company_id VARCHAR
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO raw.campaign_metadata
        SELECT
            campaign_id,
            campaign_name,
            channel,
            CAST(budget_usd AS DECIMAL(18, 2)),
            start_date,
            end_date,
            target_company_id
        FROM read_csv(
            {_sql_path(source_path)},
            header = true,
            all_varchar = true,
            nullstr = '__SOURCE_NULL__'
        )
        """
    )


def _load_content_performance(
    connection: duckdb.DuckDBPyConnection, source_path: Path
) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE raw.content_performance (
            content_id VARCHAR,
            channel VARCHAR,
            publish_date VARCHAR,
            views BIGINT,
            clicks BIGINT,
            utm_source VARCHAR,
            utm_campaign VARCHAR
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO raw.content_performance
        SELECT
            content_id,
            channel,
            publish_date,
            CAST(views AS BIGINT),
            CAST(clicks AS BIGINT),
            utm_source,
            utm_campaign
        FROM read_csv(
            {_sql_path(source_path)},
            header = true,
            all_varchar = true,
            nullstr = '__SOURCE_NULL__'
        )
        """
    )


def _load_portfolio_revenue(
    connection: duckdb.DuckDBPyConnection, source_path: Path
) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE raw.portfolio_revenue (
            revenue_id VARCHAR,
            company_id VARCHAR,
            user_id VARCHAR,
            month VARCHAR,
            revenue_amount DECIMAL(18, 2),
            is_recurring BOOLEAN
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO raw.portfolio_revenue
        SELECT
            revenue_id,
            company_id,
            user_id,
            month,
            CAST(revenue_amount AS DECIMAL(18, 2)),
            CAST(is_recurring AS BOOLEAN)
        FROM read_csv(
            {_sql_path(source_path)},
            header = true,
            all_varchar = true,
            nullstr = '__SOURCE_NULL__'
        )
        """
    )


def _load_user_signups(
    connection: duckdb.DuckDBPyConnection, source_path: Path
) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TABLE raw.user_signups (
            user_id VARCHAR,
            signup_date VARCHAR,
            company_id VARCHAR,
            referral_source VARCHAR,
            utm_source VARCHAR,
            utm_medium VARCHAR,
            utm_campaign VARCHAR,
            first_touch_channel VARCHAR,
            last_touch_channel VARCHAR
        )
        """
    )
    connection.execute(
        f"""
        INSERT INTO raw.user_signups
        SELECT
            signup.user_id,
            signup.signup_date,
            signup.company_id,
            signup.referral_source,
            signup.utm_source,
            signup.utm_medium,
            signup.utm_campaign,
            signup.first_touch_channel,
            signup.last_touch_channel
        FROM read_json_auto({_sql_path(source_path)}) AS source,
             UNNEST(source.signups) AS item(signup)
        """
    )


def load_raw(
    db_path: Path | str = DEFAULT_DB_PATH,
    data_dir: Path | str = DEFAULT_DATA_DIR,
) -> dict[str, int]:
    """Recreate all raw source tables and return their loaded row counts."""
    database_path = Path(db_path).expanduser().resolve()
    source_directory = Path(data_dir).expanduser().resolve()
    source_paths = _require_source_files(source_directory)
    database_path.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading raw data from %s", source_directory)
    LOGGER.info("DuckDB database: %s", database_path)

    loaders = {
        "campaign_metadata": _load_campaign_metadata,
        "content_performance": _load_content_performance,
        "portfolio_revenue": _load_portfolio_revenue,
        "user_signups": _load_user_signups,
    }

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("BEGIN TRANSACTION")
        connection.execute("CREATE SCHEMA IF NOT EXISTS raw")

        row_counts: dict[str, int] = {}
        for table_name, loader in loaders.items():
            loader(connection, source_paths[table_name])
            row_count = connection.execute(
                f"SELECT COUNT(*) FROM raw.{table_name}"
            ).fetchone()[0]
            row_counts[table_name] = row_count
            LOGGER.info("Loaded raw.%s: %s rows", table_name, f"{row_count:,}")

        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        LOGGER.exception("Raw ingestion failed; all table changes were rolled back")
        raise
    finally:
        connection.close()

    LOGGER.info("Raw ingestion completed successfully")
    return row_counts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"DuckDB database path (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Source data directory (default: {DEFAULT_DATA_DIR})",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = _parse_args()
    load_raw(db_path=args.db_path, data_dir=args.data_dir)


if __name__ == "__main__":
    main()
