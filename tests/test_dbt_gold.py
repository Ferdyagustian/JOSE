"""Automated verification tests for Tahap 4 (Gold Layer Data Modeling with dbt-duckdb).

Verifies Kimball Star Schema integrity, surrogate keys, referential joins,
and SCD Type 2 dimension attributes in DuckDB.
"""

from __future__ import annotations

import duckdb
import pytest

from src.config import settings

GOLD_DB_PATH = settings.local_data_dir / "gold" / "lakehouse.duckdb"


@pytest.fixture(scope="module")
def duckdb_con():
    """Fixture providing a read-only DuckDB connection to the Gold lakehouse."""
    if not GOLD_DB_PATH.exists():
        pytest.skip(f"Gold database does not exist at {GOLD_DB_PATH}")
    con = duckdb.connect(str(GOLD_DB_PATH), read_only=True)
    yield con
    con.close()


def test_gold_tables_exist(duckdb_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that all expected dimensional, fact, and snapshot tables exist in Gold."""
    expected_tables = {
        "dim_companies",
        "dim_skills",
        "dim_youtube_videos",
        "fact_job_postings",
        "bridge_job_skills",
        "scd_dim_companies",
    }
    actual_tables = {row[0] for row in duckdb_con.execute("SHOW TABLES").fetchall()}
    for table in expected_tables:
        assert table in actual_tables, f"Expected table '{table}' missing in Gold DuckDB"


def test_fact_job_postings_surrogate_keys(duckdb_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that fact_job_postings surrogate keys are valid 32-char MD5 hashes."""
    rows = duckdb_con.execute(
        "SELECT job_key, company_key, job_id, role_category FROM fact_job_postings LIMIT 10"
    ).fetchall()
    assert len(rows) > 0, "fact_job_postings should not be empty"
    for job_key, company_key, job_id, role_category in rows:
        assert len(job_key) == 32, f"job_key {job_key} is not a 32-char MD5 hash"
        assert len(company_key) == 32, f"company_key {company_key} is not a 32-char MD5 hash"
        assert job_id is not None
        assert role_category is not None


def test_dim_companies_scd2_attributes(duckdb_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that dim_companies contains SCD Type 2 validity fields."""
    cols = [col[0] for col in duckdb_con.execute("DESCRIBE dim_companies").fetchall()]
    assert "company_key" in cols
    assert "company_name" in cols
    assert "is_current" in cols
    assert "valid_from" in cols

    # Verify is_current rows are boolean
    current_count = duckdb_con.execute(
        "SELECT COUNT(*) FROM dim_companies WHERE is_current = true"
    ).fetchone()[0]
    assert current_count > 0, "Expected active current companies in dim_companies"


def test_bridge_job_skills_referential_integrity(duckdb_con: duckdb.DuckDBPyConnection) -> None:
    """Verify bridge table connects fact_job_postings and dim_skills without orphans."""
    orphan_jobs = duckdb_con.execute(
        """
        SELECT COUNT(*) 
        FROM bridge_job_skills b
        LEFT JOIN fact_job_postings f ON b.job_key = f.job_key
        WHERE f.job_key IS NULL
        """
    ).fetchone()[0]
    assert orphan_jobs == 0, "Bridge table contains job_keys not found in fact_job_postings"

    orphan_skills = duckdb_con.execute(
        """
        SELECT COUNT(*) 
        FROM bridge_job_skills b
        LEFT JOIN dim_skills s ON b.skill_key = s.skill_key
        WHERE s.skill_key IS NULL
        """
    ).fetchone()[0]
    assert orphan_skills == 0, "Bridge table contains skill_keys not found in dim_skills"


def test_youtube_learning_radar_join(duckdb_con: duckdb.DuckDBPyConnection) -> None:
    """Verify that YouTube video dimension links properly to tech skills."""
    res = duckdb_con.execute(
        """
        SELECT s.skill_name, COUNT(y.video_key) 
        FROM dim_skills s
        JOIN dim_youtube_videos y ON LOWER(s.skill_name) = LOWER(y.skill_name)
        GROUP BY s.skill_name
        """
    ).fetchall()
    assert len(res) > 0, "Expected at least one matching skill with YouTube tutorials"
