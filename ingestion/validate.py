"""Run data quality checks against the DuckDB raw schema."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "warehouse.duckdb"

VALID_COMPANY_IDS = ("CTC-001", "CTC-002", "CTC-003", "CTC-004")

EXPECTED_SCHEMAS = {
    "campaign_metadata": {
        "campaign_id": "VARCHAR",
        "campaign_name": "VARCHAR",
        "channel": "VARCHAR",
        "budget_usd": "DECIMAL(18,2)",
        "start_date": "VARCHAR",
        "end_date": "VARCHAR",
        "target_company_id": "VARCHAR",
    },
    "content_performance": {
        "content_id": "VARCHAR",
        "channel": "VARCHAR",
        "publish_date": "VARCHAR",
        "views": "BIGINT",
        "clicks": "BIGINT",
        "utm_source": "VARCHAR",
        "utm_campaign": "VARCHAR",
    },
    "portfolio_revenue": {
        "revenue_id": "VARCHAR",
        "company_id": "VARCHAR",
        "user_id": "VARCHAR",
        "month": "VARCHAR",
        "revenue_amount": "DECIMAL(18,2)",
        "is_recurring": "BOOLEAN",
    },
    "user_signups": {
        "user_id": "VARCHAR",
        "signup_date": "VARCHAR",
        "company_id": "VARCHAR",
        "referral_source": "VARCHAR",
        "utm_source": "VARCHAR",
        "utm_medium": "VARCHAR",
        "utm_campaign": "VARCHAR",
        "first_touch_channel": "VARCHAR",
        "last_touch_channel": "VARCHAR",
    },
}

REQUIRED_FIELDS = {
    "campaign_metadata": (
        "campaign_id",
        "campaign_name",
        "budget_usd",
        "start_date",
        "end_date",
    ),
    "content_performance": (
        "content_id",
        "publish_date",
        "views",
        "clicks",
    ),
    "portfolio_revenue": (
        "revenue_id",
        "company_id",
        "user_id",
        "month",
        "revenue_amount",
        "is_recurring",
    ),
    "user_signups": ("user_id", "signup_date", "company_id"),
}

PRIMARY_KEYS = {
    "campaign_metadata": "campaign_id",
    "content_performance": "content_id",
    "portfolio_revenue": "revenue_id",
    "user_signups": "user_id",
}


@dataclass(frozen=True)
class ValidationResult:
    check_name: str
    status: str
    message: str
    timestamp: datetime


class Validator:
    """Collect validation results for one DuckDB connection."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self.connection = connection
        self.results: list[ValidationResult] = []
        self.run_timestamp = datetime.now(timezone.utc)

    def add(self, check_name: str, status: str, message: str) -> None:
        self.results.append(
            ValidationResult(
                check_name=check_name,
                status=status,
                message=message,
                timestamp=self.run_timestamp,
            )
        )

    def count_issues(
        self,
        check_name: str,
        query: str,
        issue_status: str,
        pass_message: str,
        issue_message: str,
    ) -> None:
        issue_count = self.connection.execute(query).fetchone()[0]
        if issue_count == 0:
            self.add(check_name, "PASS", pass_message)
        else:
            self.add(
                check_name,
                issue_status,
                f"{issue_message}: {issue_count:,} row(s)",
            )


def _normalized_type(data_type: str) -> str:
    return data_type.upper().replace(" ", "")


def _table_names(connection: duckdb.DuckDBPyConnection) -> set[str]:
    rows = connection.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'raw'
        """
    ).fetchall()
    return {row[0] for row in rows}


def _run_schema_checks(validator: Validator) -> set[str]:
    present_tables = _table_names(validator.connection)

    for table_name, expected_columns in EXPECTED_SCHEMAS.items():
        if table_name not in present_tables:
            validator.add(
                f"table_exists_{table_name}",
                "FAIL",
                f"Required table raw.{table_name} does not exist",
            )
            continue

        validator.add(
            f"table_exists_{table_name}",
            "PASS",
            f"Required table raw.{table_name} exists",
        )
        rows = validator.connection.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'raw' AND table_name = ?
            """,
            [table_name],
        ).fetchall()
        actual_columns = {name: data_type for name, data_type in rows}
        missing_columns = sorted(set(expected_columns) - set(actual_columns))

        if missing_columns:
            validator.add(
                f"required_columns_{table_name}",
                "FAIL",
                f"Missing column(s): {', '.join(missing_columns)}",
            )
        else:
            validator.add(
                f"required_columns_{table_name}",
                "PASS",
                "All required columns are present",
            )

        invalid_types = []
        for column_name, expected_type in expected_columns.items():
            actual_type = actual_columns.get(column_name)
            if actual_type and _normalized_type(actual_type) != expected_type:
                invalid_types.append(
                    f"{column_name}={actual_type} (expected {expected_type})"
                )

        if invalid_types:
            validator.add(
                f"expected_types_{table_name}",
                "FAIL",
                "Invalid type(s): " + ", ".join(invalid_types),
            )
        else:
            validator.add(
                f"expected_types_{table_name}",
                "PASS",
                "All columns have the expected DuckDB types",
            )

    return present_tables


def _run_core_quality_checks(
    validator: Validator, present_tables: set[str]
) -> None:
    for table_name, fields in REQUIRED_FIELDS.items():
        if table_name not in present_tables:
            continue
        for field in fields:
            empty_condition = (
                f"{field} IS NULL"
                if EXPECTED_SCHEMAS[table_name][field] != "VARCHAR"
                else f"{field} IS NULL OR TRIM({field}) = ''"
            )
            validator.count_issues(
                f"required_value_{table_name}_{field}",
                f"SELECT COUNT(*) FROM raw.{table_name} WHERE {empty_condition}",
                "FAIL",
                f"raw.{table_name}.{field} has no missing values",
                f"raw.{table_name}.{field} has missing values",
            )

    for table_name, primary_key in PRIMARY_KEYS.items():
        if table_name not in present_tables:
            continue
        validator.count_issues(
            f"duplicate_primary_key_{table_name}",
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT {primary_key}
                FROM raw.{table_name}
                GROUP BY {primary_key}
                HAVING COUNT(*) > 1
            )
            """,
            "FAIL",
            f"raw.{table_name}.{primary_key} is unique",
            f"raw.{table_name}.{primary_key} contains duplicate keys",
        )

    date_checks = (
        ("campaign_start_date", "campaign_metadata", "start_date", "DATE"),
        ("campaign_end_date", "campaign_metadata", "end_date", "DATE"),
        ("content_publish_date", "content_performance", "publish_date", "DATE"),
        ("signup_date", "user_signups", "signup_date", "DATE"),
    )
    for check_name, table_name, column_name, target_type in date_checks:
        if table_name not in present_tables:
            continue
        validator.count_issues(
            f"valid_date_{check_name}",
            f"""
            SELECT COUNT(*)
            FROM raw.{table_name}
            WHERE {column_name} IS NOT NULL
              AND TRIM({column_name}) <> ''
              AND TRY_CAST({column_name} AS {target_type}) IS NULL
            """,
            "FAIL",
            f"raw.{table_name}.{column_name} contains valid dates",
            f"raw.{table_name}.{column_name} contains invalid dates",
        )

    if "portfolio_revenue" in present_tables:
        validator.count_issues(
            "valid_date_revenue_month",
            """
            SELECT COUNT(*)
            FROM raw.portfolio_revenue
            WHERE month IS NOT NULL
              AND TRIM(month) <> ''
              AND TRY_STRPTIME(month, '%Y-%m') IS NULL
            """,
            "FAIL",
            "raw.portfolio_revenue.month contains valid YYYY-MM values",
            "raw.portfolio_revenue.month contains invalid YYYY-MM values",
        )

    if "campaign_metadata" in present_tables:
        validator.count_issues(
            "valid_campaign_date_range",
            """
            SELECT COUNT(*)
            FROM raw.campaign_metadata
            WHERE TRY_CAST(start_date AS DATE) > TRY_CAST(end_date AS DATE)
            """,
            "FAIL",
            "All campaign start dates are on or before end dates",
            "Campaign start date occurs after end date",
        )

    nonnegative_checks = (
        ("campaign_budget", "campaign_metadata", "budget_usd"),
        ("content_views", "content_performance", "views"),
        ("content_clicks", "content_performance", "clicks"),
        ("revenue_amount", "portfolio_revenue", "revenue_amount"),
    )
    for check_name, table_name, column_name in nonnegative_checks:
        if table_name not in present_tables:
            continue
        validator.count_issues(
            f"nonnegative_{check_name}",
            f"SELECT COUNT(*) FROM raw.{table_name} WHERE {column_name} < 0",
            "FAIL",
            f"raw.{table_name}.{column_name} is non-negative",
            f"raw.{table_name}.{column_name} contains negative values",
        )


def _run_referential_integrity_checks(
    validator: Validator, present_tables: set[str]
) -> None:
    if {"portfolio_revenue", "user_signups"} <= present_tables:
        validator.count_issues(
            "revenue_user_exists",
            """
            SELECT COUNT(*)
            FROM raw.portfolio_revenue AS revenue
            LEFT JOIN raw.user_signups AS signup USING (user_id)
            WHERE signup.user_id IS NULL
            """,
            "FAIL",
            "Every revenue user_id exists in raw.user_signups",
            "Revenue rows reference an unknown user_id",
        )

    valid_companies = ", ".join(f"'{value}'" for value in VALID_COMPANY_IDS)
    if "portfolio_revenue" in present_tables:
        validator.count_issues(
            "valid_revenue_company",
            f"""
            SELECT COUNT(*)
            FROM raw.portfolio_revenue
            WHERE company_id NOT IN ({valid_companies})
            """,
            "FAIL",
            "Every revenue company_id is valid",
            "Revenue rows reference an invalid company_id",
        )

    if "user_signups" in present_tables:
        validator.count_issues(
            "valid_signup_company",
            f"""
            SELECT COUNT(*)
            FROM raw.user_signups
            WHERE company_id NOT IN ({valid_companies})
            """,
            "FAIL",
            "Every signup company_id is valid",
            "Signup rows reference an invalid company_id",
        )

    if "campaign_metadata" in present_tables:
        validator.count_issues(
            "valid_campaign_target_company",
            f"""
            SELECT COUNT(*)
            FROM raw.campaign_metadata
            WHERE target_company_id IS NOT NULL
              AND TRIM(target_company_id) <> ''
              AND target_company_id NOT IN ({valid_companies})
            """,
            "FAIL",
            "Every populated campaign target_company_id is valid",
            "Campaign rows reference an invalid target_company_id",
        )


def _run_attribution_warning_checks(
    validator: Validator, present_tables: set[str]
) -> None:
    optional_field_checks = (
        ("content_utm_source", "content_performance", "utm_source"),
        ("content_utm_campaign", "content_performance", "utm_campaign"),
        ("signup_utm_source", "user_signups", "utm_source"),
        ("signup_utm_medium", "user_signups", "utm_medium"),
        ("signup_utm_campaign", "user_signups", "utm_campaign"),
        ("campaign_channel", "campaign_metadata", "channel"),
        ("content_channel", "content_performance", "channel"),
        ("signup_first_touch_channel", "user_signups", "first_touch_channel"),
        ("signup_last_touch_channel", "user_signups", "last_touch_channel"),
    )
    for check_name, table_name, column_name in optional_field_checks:
        if table_name not in present_tables:
            continue
        validator.count_issues(
            f"missing_attribution_{check_name}",
            f"""
            SELECT COUNT(*)
            FROM raw.{table_name}
            WHERE {column_name} IS NULL OR TRIM({column_name}) = ''
            """,
            "WARN",
            f"raw.{table_name}.{column_name} has no missing values",
            f"raw.{table_name}.{column_name} has missing values",
        )

    if "user_signups" not in present_tables:
        return

    validator.count_issues(
        "conflicting_first_last_touch",
        """
        SELECT COUNT(*)
        FROM raw.user_signups
        WHERE first_touch_channel IS NOT NULL
          AND last_touch_channel IS NOT NULL
          AND TRIM(first_touch_channel) <> ''
          AND TRIM(last_touch_channel) <> ''
          AND LOWER(first_touch_channel) <> LOWER(last_touch_channel)
        """,
        "WARN",
        "First-touch and last-touch channels agree for all signups",
        "Signups have different first-touch and last-touch channels",
    )
    validator.count_issues(
        "conflicting_utm_first_touch",
        """
        SELECT COUNT(*)
        FROM raw.user_signups
        WHERE utm_source IS NOT NULL
          AND first_touch_channel IS NOT NULL
          AND TRIM(utm_source) <> ''
          AND TRIM(first_touch_channel) <> ''
          AND LOWER(utm_source) <> LOWER(first_touch_channel)
        """,
        "WARN",
        "Populated UTM sources agree with first-touch channels",
        "Signups have conflicting UTM source and first-touch channel",
    )
    validator.count_issues(
        "conflicting_referral_utm",
        """
        SELECT COUNT(*)
        FROM raw.user_signups
        WHERE referral_source IS NOT NULL
          AND utm_source IS NOT NULL
          AND TRIM(referral_source) <> ''
          AND TRIM(utm_source) <> ''
          AND LOWER(referral_source) NOT IN ('direct', 'word_of_mouth')
          AND LOWER(referral_source) <> LOWER(utm_source)
        """,
        "WARN",
        "Comparable referral sources agree with populated UTM sources",
        "Signups have conflicting referral and UTM sources",
    )


def _save_results(
    connection: duckdb.DuckDBPyConnection, results: list[ValidationResult]
) -> None:
    connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS raw.validation_results (
            check_name VARCHAR,
            status VARCHAR,
            message VARCHAR,
            "timestamp" TIMESTAMPTZ
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO raw.validation_results
            (check_name, status, message, "timestamp")
        VALUES (?, ?, ?, ?)
        """,
        [
            (result.check_name, result.status, result.message, result.timestamp)
            for result in results
        ],
    )


def _print_summary(results: list[ValidationResult], db_path: Path) -> None:
    counts = {
        status: sum(result.status == status for result in results)
        for status in ("PASS", "WARN", "FAIL")
    }
    print("\nRaw data validation")
    print(f"Database: {db_path}")
    print(
        "Summary: "
        f"{counts['PASS']} PASS | {counts['WARN']} WARN | {counts['FAIL']} FAIL"
    )
    print("-" * 88)
    for result in results:
        print(f"[{result.status:<4}] {result.check_name}: {result.message}")
    print("-" * 88)
    print("Results saved to raw.validation_results")


def validate_database(
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[ValidationResult]:
    """Run validations, persist results, and return the current run's findings."""
    database_path = Path(db_path).expanduser().resolve()
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("CREATE SCHEMA IF NOT EXISTS raw")
        validator = Validator(connection)
        present_tables = _run_schema_checks(validator)
        _run_core_quality_checks(validator, present_tables)
        _run_referential_integrity_checks(validator, present_tables)
        _run_attribution_warning_checks(validator, present_tables)
        _save_results(connection, validator.results)
    finally:
        connection.close()

    _print_summary(validator.results, database_path)
    return validator.results


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"DuckDB database path (default: {DEFAULT_DB_PATH})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    results = validate_database(db_path=args.db_path)
    if any(result.status == "FAIL" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
