"""Unit tests for Streamlit Dashboard queries, caching, and styling modules.

Ensures analytical queries execute cleanly against DuckDB Gold layer
and handle edge cases / filters gracefully without errors.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from dashboard.queries import (
    get_filter_options,
    get_jobs_explorer,
    get_kpis,
    get_role_distribution,
    get_salary_insights,
    get_top_skills,
    get_work_policy_distribution,
    get_youtube_radar,
)
from dashboard.styles import apply_dark_chart_theme


def test_get_kpis_structure_and_values() -> None:
    """Verify get_kpis returns valid dictionary structure with correct types."""
    kpis = get_kpis()
    assert isinstance(kpis, dict)
    assert "total_jobs" in kpis
    assert "total_companies" in kpis
    assert "remote_pct" in kpis
    assert "top_skill" in kpis
    assert "total_videos" in kpis

    assert isinstance(kpis["total_jobs"], int)
    assert isinstance(kpis["total_companies"], int)
    assert isinstance(kpis["remote_pct"], (int, float))
    assert isinstance(kpis["top_skill"], str)
    assert isinstance(kpis["total_videos"], int)


def test_get_filter_options() -> None:
    """Verify get_filter_options returns non-empty distinct lists."""
    filters = get_filter_options()
    assert isinstance(filters, dict)
    assert "roles" in filters
    assert "work_policies" in filters
    assert "skills" in filters
    assert isinstance(filters["roles"], list)
    assert isinstance(filters["work_policies"], list)
    assert isinstance(filters["skills"], list)


def test_get_top_skills() -> None:
    """Verify get_top_skills returns structured DataFrame with expected columns."""
    df = get_top_skills(limit=10)
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "skill_name" in df.columns
        assert "skill_category" in df.columns
        assert "job_count" in df.columns
        assert df["job_count"].iloc[0] >= df["job_count"].iloc[-1]


def test_get_top_skills_filtered() -> None:
    """Verify get_top_skills handles specific role filter gracefully."""
    df = get_top_skills(limit=5, role_filter="Software Engineering")
    assert isinstance(df, pd.DataFrame)


def test_get_work_policy_distribution() -> None:
    """Verify get_work_policy_distribution returns work_policy breakdown."""
    df = get_work_policy_distribution()
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "work_policy" in df.columns
        assert "total_jobs" in df.columns


def test_get_role_distribution() -> None:
    """Verify get_role_distribution returns role categories."""
    df = get_role_distribution()
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "role_category" in df.columns
        assert "total_postings" in df.columns


def test_get_salary_insights() -> None:
    """Verify get_salary_insights returns salary statistics."""
    df = get_salary_insights()
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "role_category" in df.columns
        assert "avg_sal_jt" in df.columns


def test_get_jobs_explorer_unfiltered() -> None:
    """Verify get_jobs_explorer returns job postings with formatted salary and location."""
    df = get_jobs_explorer(limit=10)
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "job_title" in df.columns
        assert "company_name" in df.columns
        assert "salary_display" in df.columns
        assert "company_location" in df.columns
        assert "job_url" in df.columns

        # Verify salary format ('Gaji tidak ditampilkan' or 'Rp ...') and location template ('Indonesia, <Kota>')
        for _, row in df.iterrows():
            sal_text = str(row["salary_display"])
            loc_text = str(row["company_location"])
            assert "nan" not in sal_text.lower(), f"Unexpected 'nan' in salary: {sal_text}"
            assert sal_text == "Gaji tidak ditampilkan" or "Rp" in sal_text, f"Unexpected salary text: {sal_text}"
            assert loc_text.startswith("Indonesia, "), f"Location must follow 'Indonesia, <Kota>' template: {loc_text}"
            assert "typename" not in loc_text.lower(), f"Unexpected 'typename' in location: {loc_text}"


def test_get_jobs_explorer_with_filters() -> None:
    """Verify get_jobs_explorer handles search keyword and policies."""
    df = get_jobs_explorer(
        role="All Roles",
        work_policy="Remote",
        search_keyword="engineer",
        limit=5,
    )
    assert isinstance(df, pd.DataFrame)


def test_get_youtube_radar() -> None:
    """Verify get_youtube_radar returns video recommendations."""
    df = get_youtube_radar(limit=6)
    assert isinstance(df, pd.DataFrame)
    if not df.empty:
        assert "video_id" in df.columns
        assert "skill_name" in df.columns
        assert "video_title" in df.columns
        assert "channel_name" in df.columns
        assert "view_count" in df.columns
        assert "video_url" in df.columns


def test_apply_dark_chart_theme() -> None:
    """Verify apply_dark_chart_theme applies glassmorphism layout to Plotly figures."""
    fig = go.Figure(data=[go.Bar(x=["Python", "SQL"], y=[10, 20])])
    themed_fig = apply_dark_chart_theme(fig, height=350)
    assert themed_fig.layout.template is not None
    assert themed_fig.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert themed_fig.layout.height == 350
