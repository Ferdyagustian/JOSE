"""Unit tests for Silver Layer normalization, role classification, and pipeline deduplication."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from src.spark_jobs.bronze_to_silver_jobs import (
    classify_role_category,
    clean_and_transform_job,
    normalize_employment_type,
    normalize_experience_level,
    normalize_location,
    normalize_salary,
    normalize_work_policy,
    run_silver_pipeline,
)


def test_normalize_location() -> None:
    """Test location normalization into 'Indonesia, <Kota>' template."""
    assert normalize_location(None) == "Indonesia, Jakarta"
    assert normalize_location("") == "Indonesia, Jakarta"
    assert normalize_location("nan") == "Indonesia, Jakarta"
    assert normalize_location("Jakarta") == "Indonesia, Jakarta"
    assert normalize_location("Bandung, Jawa Barat") == "Indonesia, Bandung"
    assert normalize_location("Indonesia, Surabaya") == "Indonesia, Surabaya"
    assert normalize_location("Kabupaten Sleman") == "Indonesia, Sleman"
    assert normalize_location("Kota Tangerang Selatan") == "Indonesia, Tangerang Selatan"

    # Glints GraphQL/Next.js dict or stringified dict with __typename
    glints_loc = {
        "__typename": "HierarchicalLocation",
        "name": "Jakarta Selatan",
        "parents": [{"administrativeLevelName": "City", "name": "Jakarta"}],
    }
    assert normalize_location(glints_loc) == "Indonesia, Jakarta"
    assert normalize_location(str(glints_loc)) == "Indonesia, Jakarta"


def test_normalize_employment_type() -> None:
    """Test normalization of various raw employment type strings."""
    assert normalize_employment_type("Full Time") == "Full-Time"
    assert normalize_employment_type("Permanent") == "Full-Time"
    assert normalize_employment_type("Kontrak") == "Contract"
    assert normalize_employment_type("Freelance Project") == "Contract"
    assert normalize_employment_type("Magang / Intern") == "Internship"
    assert normalize_employment_type("Paruh Waktu") == "Part-Time"
    assert normalize_employment_type(None) == "Full-Time"


def test_normalize_experience_level() -> None:
    """Test experience level mapping."""
    assert normalize_experience_level("Fresh Graduate") == "Fresh Graduate / Entry"
    assert normalize_experience_level("Lulusan baru") == "Fresh Graduate / Entry"
    assert normalize_experience_level("1-3 years") == "Junior (1-3 yrs)"
    assert normalize_experience_level("3-5 yrs") == "Mid-Senior (3-5 yrs)"
    assert normalize_experience_level("Senior Data Engineer 5+ yrs") == "Senior (5+ yrs)"
    assert normalize_experience_level("Lead Architect") == "Senior (5+ yrs)"
    assert normalize_experience_level(None) == "Unspecified"


def test_normalize_work_policy() -> None:
    """Test work policy mapping."""
    assert normalize_work_policy("Remote (WFH)") == "Remote"
    assert normalize_work_policy("Hybrid Kerja Fleksibel") == "Hybrid"
    assert normalize_work_policy("On-site Office") == "WFO"
    assert normalize_work_policy(None) == "WFO"


def test_classify_role_category() -> None:
    """Test tech role keyword classification."""
    assert classify_role_category("Senior Data Engineer") == "Data Engineer"
    assert classify_role_category("ETL Big Data Developer") == "Data Engineer"
    assert (
        classify_role_category("BI Analyst / Business Intelligence") == "Data Analyst / Scientist"
    )
    assert classify_role_category("AI / Machine Learning Engineer") == "AI / ML Engineer"
    assert classify_role_category("Backend Golang Engineer") == "Backend Engineer"
    assert classify_role_category("React Frontend Developer") == "Frontend / Fullstack"
    assert classify_role_category("DevOps & SRE Specialist") == "DevOps / Cloud"
    assert classify_role_category("Android Mobile Engineer") == "Mobile Developer"
    assert classify_role_category("QA Automation Tester") == "QA / Security"
    assert classify_role_category("General IT Support") == "Other IT"


def test_normalize_salary() -> None:
    """Test salary parsing and USD to IDR conversion."""
    # IDR salary
    s_min, s_max = normalize_salary(10000000.0, 15000000.0, "IDR")
    assert s_min == 10000000.0
    assert s_max == 15000000.0

    # USD salary converted to IDR
    s_min_usd, s_max_usd = normalize_salary(1000.0, 2000.0, "USD")
    assert s_min_usd == 16000000.0
    assert s_max_usd == 32000000.0

    # Inverted min/max handles gracefully
    s_inv_min, s_inv_max = normalize_salary(20000000.0, 10000000.0, "IDR")
    assert s_inv_min == 10000000.0
    assert s_inv_max == 20000000.0


def test_clean_and_transform_job() -> None:
    """Test full single-job record transformation."""
    raw = {
        "job_id": "job-101",
        "source": "glints",
        "job_title": "Senior Data Engineer",
        "company_name": "Traveloka",
        "company_industry": "Travel Tech",
        "company_location": "Jakarta",
        "employment_type": "Permanent",
        "work_policy": "Remote",
        "experience_level": "3-5 yrs",
        "salary_min": 18000000.0,
        "salary_max": 28000000.0,
        "currency": "IDR",
        "job_description": "We need expertise in PySpark, dbt, Snowflake, and Airflow.",
        "job_url": "https://example.com/job-101",
    }
    clean_job, skills = clean_and_transform_job(raw)

    assert clean_job["job_id"] == "job-101"
    assert clean_job["role_category"] == "Data Engineer"
    assert clean_job["employment_type"] == "Full-Time"
    assert clean_job["work_policy"] == "Remote"
    assert clean_job["salary_min_idr"] == 18000000.0

    skill_names = {s["skill_name"] for s in skills}
    assert "PySpark" in skill_names
    assert "dbt" in skill_names
    assert "Snowflake" in skill_names
    assert "Airflow" in skill_names


def test_run_silver_pipeline_with_deduplication(tmp_path: Path) -> None:
    """Test that duplicate jobs are cleanly deduplicated in Silver layer."""
    bronze_dir = tmp_path / "bronze" / "jobs" / "source=glints" / "dt=2026-10-18"
    bronze_dir.mkdir(parents=True, exist_ok=True)

    # 3 records where job-1 is duplicated with updated salary
    records = [
        {
            "job_id": "job-1",
            "source": "glints",
            "job_title": "Data Engineer",
            "company_name": "Company A",
            "salary_min": 10000000.0,
            "salary_max": 15000000.0,
            "currency": "IDR",
            "job_description": "PySpark expert required.",
        },
        {
            "job_id": "job-2",
            "source": "glints",
            "job_title": "Backend Engineer",
            "company_name": "Company B",
            "salary_min": 12000000.0,
            "salary_max": 18000000.0,
            "currency": "IDR",
            "job_description": "Golang and Docker.",
        },
        {
            # Updated version of job-1 in subsequent batch
            "job_id": "job-1",
            "source": "glints",
            "job_title": "Data Engineer",
            "company_name": "Company A",
            "salary_min": 12000000.0,  # updated salary
            "salary_max": 17000000.0,
            "currency": "IDR",
            "job_description": "PySpark and dbt expert required.",
        },
    ]

    pq.write_table(pa.Table.from_pylist(records), bronze_dir / "data.parquet")

    summary = run_silver_pipeline(base_dir=tmp_path)
    assert summary["jobs_processed"] == 2  # job-1 and job-2 (deduplicated!)

    # Verify DuckDB can query the resulting Silver parquet
    con = duckdb.connect(":memory:")
    jobs_count = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{tmp_path}/silver/delta_jobs/*.parquet')"
    ).fetchone()[0]
    q_salary = (
        f"SELECT salary_min_idr FROM read_parquet('{tmp_path}/silver/delta_jobs/*.parquet') "
        "WHERE job_id = 'job-1'"
    )
    updated_salary = con.execute(q_salary).fetchone()[0]
    con.close()

    assert jobs_count == 2
    assert updated_salary == 12000000.0  # verifies the upsert updated to latest value!
