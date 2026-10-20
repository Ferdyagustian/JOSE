"""Analytical query engine for Streamlit Dashboard querying DuckDB Gold Lakehouse.

Utilizes in-memory caching (@st.cache_data) for sub-50ms interactive query performance.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import math

import duckdb
import pandas as pd
import streamlit as st

from src.config import settings
from src.spark_jobs.bronze_to_silver_jobs import normalize_location

logger = logging.getLogger(__name__)

GOLD_DB_PATH = settings.local_data_dir / "gold" / "lakehouse.duckdb"


def get_db_connection() -> duckdb.DuckDBPyConnection | None:
    """Obtain a thread-safe read-only connection to the Gold DuckDB database."""
    if not GOLD_DB_PATH.exists():
        logger.warning("Gold DuckDB file not found at %s", GOLD_DB_PATH)
        return None
    try:
        return duckdb.connect(str(GOLD_DB_PATH), read_only=True)
    except Exception as exc:
        logger.error("Failed to connect to Gold DuckDB: %s", exc)
        return None


@st.cache_data(ttl=300)
def get_kpis() -> dict[str, Any]:
    """Retrieve top-level KPI metrics for the executive banner."""
    con = get_db_connection()
    defaults = {
        "total_jobs": 0,
        "total_companies": 0,
        "remote_pct": 0.0,
        "top_skill": "N/A",
        "top_skill_count": 0,
        "total_videos": 0,
    }
    if not con:
        return defaults

    try:
        # Job and company metrics
        job_stats = con.execute(
            """
            SELECT 
                COUNT(*) AS total_jobs,
                COUNT(DISTINCT company_name) AS total_companies,
                ROUND(COUNT(CASE WHEN work_policy = 'Remote' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 1) AS remote_pct
            FROM fact_job_postings
            """
        ).fetchone()

        # Top skill in demand
        top_skill_row = con.execute(
            """
            SELECT skill_name, COUNT(*) AS cnt
            FROM bridge_job_skills
            GROUP BY 1
            ORDER BY cnt DESC
            LIMIT 1
            """
        ).fetchone()

        # YouTube video resources
        video_count = con.execute("SELECT COUNT(*) FROM dim_youtube_videos").fetchone()[0]

        return {
            "total_jobs": job_stats[0] if job_stats else 0,
            "total_companies": job_stats[1] if job_stats else 0,
            "remote_pct": job_stats[2] if job_stats and job_stats[2] is not None else 0.0,
            "top_skill": top_skill_row[0] if top_skill_row else "SQL",
            "top_skill_count": top_skill_row[1] if top_skill_row else 0,
            "total_videos": video_count,
        }
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_filter_options() -> dict[str, list[str]]:
    """Fetch distinct filter values for sidebar dropdowns."""
    con = get_db_connection()
    if not con:
        return {"roles": [], "work_policies": [], "skills": []}

    try:
        roles = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT role_category FROM fact_job_postings WHERE role_category IS NOT NULL ORDER BY 1"
            ).fetchall()
        ]
        policies = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT work_policy FROM fact_job_postings WHERE work_policy IS NOT NULL ORDER BY 1"
            ).fetchall()
        ]
        skills = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT skill_name FROM dim_skills WHERE skill_name IS NOT NULL ORDER BY 1"
            ).fetchall()
        ]
        employment_types = [
            r[0]
            for r in con.execute(
                "SELECT DISTINCT employment_type FROM fact_job_postings WHERE employment_type IS NOT NULL ORDER BY 1"
            ).fetchall()
        ]
        return {
            "roles": roles,
            "work_policies": policies,
            "skills": skills,
            "employment_types": employment_types,
        }
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_top_skills(
    limit: int = 15,
    role_filter: str | None = None,
    work_policy_filter: str | None = None,
) -> pd.DataFrame:
    """Retrieve top in-demand technical skills matching active filters."""
    con = get_db_connection()
    if not con:
        return pd.DataFrame()

    try:
        where_clauses = ["1=1"]
        params: list[Any] = []

        if role_filter and role_filter != "All Roles":
            where_clauses.append("f.role_category = ?")
            params.append(role_filter)

        if work_policy_filter and work_policy_filter != "All Policies":
            where_clauses.append("f.work_policy = ?")
            params.append(work_policy_filter)

        where_sql = " AND ".join(where_clauses)
        params.append(limit)

        query = f"""
        SELECT 
            b.skill_name,
            b.skill_category,
            COUNT(DISTINCT b.job_key) AS job_count
        FROM bridge_job_skills b
        JOIN fact_job_postings f ON b.job_key = f.job_key
        WHERE {where_sql}
        GROUP BY b.skill_name, b.skill_category
        ORDER BY job_count DESC, b.skill_name ASC
        LIMIT ?
        """
        return con.execute(query, params).df()
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_role_distribution() -> pd.DataFrame:
    """Retrieve role breakdown with salary disclosures."""
    con = get_db_connection()
    if not con:
        return pd.DataFrame()

    try:
        query = """
        SELECT 
            role_category,
            COUNT(*) AS total_postings,
            COUNT(CASE WHEN has_salary_disclosed THEN 1 END) AS disclosed_salary_postings,
            ROUND(AVG(salary_avg_idr) / 1000000, 1) AS avg_salary_jt
        FROM fact_job_postings
        GROUP BY 1
        ORDER BY total_postings DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_work_policy_distribution() -> pd.DataFrame:
    """Retrieve breakdown of Work Policy (Remote / Hybrid / WFO)."""
    con = get_db_connection()
    if not con:
        return pd.DataFrame()

    try:
        query = """
        SELECT 
            work_policy,
            COUNT(*) AS total_jobs
        FROM fact_job_postings
        GROUP BY 1
        ORDER BY total_jobs DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_salary_insights() -> pd.DataFrame:
    """Retrieve salary benchmarks for roles with disclosed compensation."""
    con = get_db_connection()
    if not con:
        return pd.DataFrame()

    try:
        query = """
        SELECT 
            role_category,
            ROUND(MIN(salary_min_idr) / 1000000, 1) AS min_sal_jt,
            ROUND(AVG(salary_avg_idr) / 1000000, 1) AS avg_sal_jt,
            ROUND(MAX(salary_max_idr) / 1000000, 1) AS max_sal_jt,
            COUNT(*) AS sample_size
        FROM fact_job_postings
        WHERE has_salary_disclosed = true AND salary_avg_idr IS NOT NULL AND salary_avg_idr > 0
        GROUP BY 1
        ORDER BY avg_sal_jt DESC
        """
        return con.execute(query).df()
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_jobs_explorer(
    role: str | None = None,
    work_policy: str | None = None,
    skill: str | None = None,
    search_keyword: str | None = None,
    employment_type: str | None = None,
    limit: int = 100,
) -> pd.DataFrame:
    """Retrieve filtered job postings for interactive exploration."""
    con = get_db_connection()
    if not con:
        return pd.DataFrame()

    try:
        where_clauses = ["1=1"]
        params: list[Any] = []

        if role and role != "All Roles":
            where_clauses.append("f.role_category = ?")
            params.append(role)

        if work_policy and work_policy != "All Policies":
            where_clauses.append("f.work_policy = ?")
            params.append(work_policy)

        if employment_type and employment_type != "All Types":
            where_clauses.append("f.employment_type = ?")
            params.append(employment_type)

        if skill and skill != "All Skills":
            where_clauses.append(
                "f.job_key IN (SELECT job_key FROM bridge_job_skills WHERE skill_name = ?)"
            )
            params.append(skill)

        if search_keyword and search_keyword.strip():
            kw = f"%{search_keyword.strip().lower()}%"
            where_clauses.append(
                "(LOWER(f.job_title) LIKE ? OR LOWER(f.company_name) LIKE ? OR LOWER(f.job_description) LIKE ?)"
            )
            params.extend([kw, kw, kw])

        where_sql = " AND ".join(where_clauses)
        params.append(limit)

        query = f"""
        SELECT 
            f.job_title,
            f.company_name,
            f.role_category,
            f.employment_type,
            f.work_policy,
            f.company_location,
            f.salary_min_idr,
            f.salary_max_idr,
            f.has_salary_disclosed,
            f.source_portal,
            f.job_url,
            COALESCE(f.posted_date, 'Recent') AS posted_date
        FROM fact_job_postings f
        WHERE {where_sql}
        ORDER BY f.posted_date DESC, f.job_title ASC
        LIMIT ?
        """
        df = con.execute(query, params).df()

        # Format salary string with explicit user label 'Gaji tidak ditampilkan'
        def format_salary(row: pd.Series) -> str:
            if not row.get("has_salary_disclosed"):
                return "Gaji tidak ditampilkan"
            min_sal = row.get("salary_min_idr")
            max_sal = row.get("salary_max_idr")

            def is_valid_num(v: Any) -> bool:
                if v is None or pd.isna(v):
                    return False
                try:
                    f = float(v)
                    return not math.isnan(f) and not math.isinf(f) and f > 0
                except (ValueError, TypeError):
                    return False

            has_min = is_valid_num(min_sal)
            has_max = is_valid_num(max_sal)
            if has_min and has_max:
                return f"Rp {float(min_sal):,.0f} - {float(max_sal):,.0f}".replace(",", ".")
            if has_min:
                return f"Mulai Rp {float(min_sal):,.0f}".replace(",", ".")
            if has_max:
                return f"s/d Rp {float(max_sal):,.0f}".replace(",", ".")
            return "Gaji tidak ditampilkan"

        def clean_location(loc: Any) -> str:
            return normalize_location(loc)

        if not df.empty:
            df["salary_display"] = df.apply(format_salary, axis=1)
            df["company_location"] = df["company_location"].apply(clean_location)

        return df
    finally:
        con.close()


@st.cache_data(ttl=300)
def get_youtube_radar(selected_skills: list[str] | None = None, limit: int = 12) -> pd.DataFrame:
    """Retrieve YouTube tutorial recommendations matched to tech skills."""
    con = get_db_connection()
    if not con:
        return pd.DataFrame()

    try:
        where_sql = "1=1"
        params: list[Any] = []

        if selected_skills:
            placeholders = ", ".join(["?"] * len(selected_skills))
            where_sql = f"LOWER(skill_name) IN ({placeholders})"
            params.extend([s.lower() for s in selected_skills])

        params.append(limit)

        query = f"""
        SELECT 
            video_id,
            skill_name,
            video_title,
            channel_name,
            view_count,
            video_url,
            thumbnail_url
        FROM dim_youtube_videos
        WHERE {where_sql}
        ORDER BY view_count DESC
        LIMIT ?
        """
        return con.execute(query, params).df()
    finally:
        con.close()
