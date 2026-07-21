"""Tests for the raw DuckDB ingestion layer."""

from __future__ import annotations

import importlib
from pathlib import Path

import duckdb
import pytest

from ingestion.load_raw import load_raw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATA_DIR = PROJECT_ROOT / "data"
EXPECTED_RAW_TABLES = {
    "campaign_metadata",
    "content_performance",
    "portfolio_revenue",
    "user_signups",
}


@pytest.fixture()
def ingested_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "test_warehouse.duckdb"
    load_raw(db_path=database_path, data_dir=SOURCE_DATA_DIR)
    return database_path


def test_ingestion_module_imports() -> None:
    module = importlib.import_module("ingestion.load_raw")
    assert callable(module.load_raw)


def test_ingestion_creates_duckdb_database(ingested_database: Path) -> None:
    assert ingested_database.is_file()


def test_ingestion_creates_expected_raw_tables(ingested_database: Path) -> None:
    with duckdb.connect(str(ingested_database), read_only=True) as connection:
        table_rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
            """
        ).fetchall()

    actual_tables = {row[0] for row in table_rows}
    assert EXPECTED_RAW_TABLES <= actual_tables
