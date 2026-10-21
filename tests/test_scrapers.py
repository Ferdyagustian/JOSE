"""Comprehensive unit tests for Bronze Ingestion Layer (Scrapers & YouTube Fetcher).

Tests validate Pydantic schemas, parser logic, circuit breaker resilience,
TTL cache guards, and Parquet storage persistence.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb

from src.ingestion.glints_scraper import GlintsScraper
from src.ingestion.jobstreet_scraper import JobStreetScraper
from src.ingestion.schemas import JobPostingRaw, YouTubeVideoRaw
from src.ingestion.storage import (
    download_bronze_from_azure,
    load_all_cached_youtube_skills,
    save_raw_jobs,
    save_raw_youtube_videos,
    upload_file_to_azure,
)
from src.ingestion.youtube_fetcher import YouTubeFetcher

# --- Schema Tests ---


def test_job_posting_raw_validation() -> None:
    """Test valid JobPostingRaw instantiation and sanitation."""
    job = JobPostingRaw(
        job_id="test-123",
        source="glints",
        job_title="Senior Data Engineer",
        company_name="GoTo Financial",
        company_location="Jakarta",
        salary_min=15000000.0,
        salary_max=25000000.0,
        job_description="Must know PySpark, dbt, and Kafka.",
        job_url="https://glints.com/id/opportunities/jobs/test-123",
    )
    assert job.job_id == "test-123"
    assert job.source == "glints"
    assert job.company_name == "GoTo Financial"
    assert job.salary_min == 15000000.0
    assert job.currency == "IDR"
    assert job.scraped_at is not None


def test_job_posting_raw_sanitization() -> None:
    """Test that null company or title get sanitized to reasonable defaults."""
    job = JobPostingRaw(
        job_id="test-456",
        source="jobstreet",
        job_title="",
        company_name=None,
    )
    assert job.company_name == "Confidential Company"
    assert job.job_title == "Software Engineer"


def test_youtube_video_raw_validation() -> None:
    """Test valid YouTubeVideoRaw model."""
    video = YouTubeVideoRaw(
        video_id="abc12345",
        skill_name="PySpark",
        video_title="PySpark Tutorial for Beginners",
        channel_name="FreeCodeCamp",
        view_count=250000,
        video_url="https://www.youtube.com/watch?v=abc12345",
    )
    assert video.video_id == "abc12345"
    assert video.skill_name == "PySpark"
    assert video.view_count == 250000
    assert video.like_count == 0


# --- Glints Scraper Tests ---


def test_glints_scraper_parsing() -> None:
    """Test that Glints parser correctly extracts attributes from sample Next.js item."""
    scraper = GlintsScraper()
    mock_item = {
        "id": "glints-001",
        "title": "Backend Go Developer",
        "company": {"name": "Tokopedia", "industry": "E-Commerce"},
        "city": "Jakarta Selatan",
        "type": "Full-Time",
        "workArrangementOption": "Hybrid",
        "minYearsOfExperience": 2,
        "maxYearsOfExperience": 5,
        "salaries": [{"minAmount": 12000000, "maxAmount": 20000000, "currencyCode": "IDR"}],
        "skills": [{"name": "Golang"}, {"name": "PostgreSQL"}, {"name": "Docker"}],
        "createdAt": "2026-10-18T00:00:00Z",
    }

    job = scraper._parse_job_item(mock_item)
    assert job is not None
    assert job.job_id == "glints-001"
    assert job.source == "glints"
    assert job.job_title == "Backend Go Developer"
    assert job.company_name == "Tokopedia"
    assert job.company_location == "Jakarta Selatan"
    assert job.work_policy == "Hybrid"
    assert job.salary_min == 12000000.0
    assert job.salary_max == 20000000.0
    assert "Golang" in job.job_description


def test_glints_scraper_circuit_breaker() -> None:
    """Test that Glints scraper handles 403 gracefully without raising exceptions."""
    scraper = GlintsScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch.object(scraper.session, "get", return_value=mock_resp):
        jobs = scraper.fetch_jobs(max_retries=1)
        assert jobs == []


# --- JobStreet Scraper Tests ---


def test_jobstreet_scraper_parsing() -> None:
    """Test that JobStreet parser correctly extracts attributes from SEEK item."""
    scraper = JobStreetScraper()
    mock_item = {
        "id": 889911,
        "title": "Data Engineer (Remote)",
        "advertiser": {"description": "PT Tech Nusantara"},
        "location": "Jakarta",
        "area": "Jabodetabek",
        "workType": "Full-Time",
        "salary": "IDR 15.000.000 - IDR 22.000.000 per month",
        "teaser": "Work from home full time opportunity building data pipelines.",
        "bulletPoints": ["Experience with Spark and dbt", "Python & SQL expertise"],
        "listingDate": "2026-10-18T02:00:00.000Z",
    }

    job = scraper._parse_job_item(mock_item)
    assert job is not None
    assert job.job_id == "889911"
    assert job.source == "jobstreet"
    assert job.company_name == "PT Tech Nusantara"
    assert job.work_policy == "Remote"
    assert job.salary_min == 15000000.0
    assert job.salary_max == 22000000.0
    assert "Spark" in job.job_description


def test_jobstreet_scraper_circuit_breaker() -> None:
    """Test that JobStreet scraper handles 429 rate limit gracefully."""
    scraper = JobStreetScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 429

    with patch.object(scraper.session, "get", return_value=mock_resp):
        jobs = scraper.fetch_jobs(max_retries=1)
        assert jobs == []


# --- YouTube Fetcher Tests ---


def test_youtube_fetcher_fallback_generator() -> None:
    """Test that offline/no-key mode returns high quality fallback tutorial videos."""
    fetcher = YouTubeFetcher(api_key=None)
    videos = fetcher.fetch_videos_for_skill("PySpark")
    assert len(videos) >= 1
    assert videos[0].skill_name == "PySpark"
    assert "pyspark" in videos[0].video_title.lower()
    assert videos[0].video_url.startswith("https://www.youtube.com/watch?v=")


# --- Storage Tests ---


def test_storage_save_and_query_raw_jobs(tmp_path: Path) -> None:
    """Test saving raw jobs to Parquet and querying them with DuckDB."""
    sample_jobs = [
        JobPostingRaw(
            job_id="job-1",
            source="glints",
            job_title="Data Engineer",
            company_name="Company A",
            salary_min=10000000.0,
            salary_max=15000000.0,
        ),
        JobPostingRaw(
            job_id="job-2",
            source="jobstreet",
            job_title="Backend Engineer",
            company_name="Company B",
            salary_min=12000000.0,
            salary_max=18000000.0,
        ),
    ]

    saved_files = save_raw_jobs(sample_jobs, base_dir=tmp_path)
    assert len(saved_files) == 2

    # Query saved parquet using DuckDB
    con = duckdb.connect(":memory:")
    res = con.execute(
        f"SELECT COUNT(*) as total FROM read_parquet('{tmp_path}/bronze/jobs/**/*.parquet')"
    ).fetchone()
    con.close()

    assert res is not None
    assert res[0] == 2


def test_storage_save_and_cache_youtube_videos(tmp_path: Path) -> None:
    """Test saving YouTube videos and querying cached skill names."""
    videos = [
        YouTubeVideoRaw(
            video_id="v1",
            skill_name="dbt",
            video_title="dbt Tutorial",
            channel_name="Channel 1",
            view_count=50000,
            video_url="https://youtube.com/watch?v=v1",
        ),
        YouTubeVideoRaw(
            video_id="v2",
            skill_name="Docker",
            video_title="Docker Guide",
            channel_name="Channel 2",
            view_count=80000,
            video_url="https://youtube.com/watch?v=v2",
        ),
    ]

    save_path = save_raw_youtube_videos(videos, base_dir=tmp_path)
    assert save_path is not None
    assert save_path.exists()

    cached_skills = load_all_cached_youtube_skills(base_dir=tmp_path)
    assert "dbt" in cached_skills
    assert "Docker" in cached_skills
    assert "PySpark" not in cached_skills


def test_upload_file_to_azure_unconfigured(tmp_path: Path) -> None:
    """Verify upload_file_to_azure returns False when unconfigured."""
    dummy_file = tmp_path / "dummy.parquet"
    dummy_file.write_text("dummy")
    with patch("src.ingestion.storage.settings.azure_storage_connection_string", ""):
        assert not upload_file_to_azure(dummy_file, "dummy.parquet")


def test_upload_file_to_azure_configured(tmp_path: Path) -> None:
    """Verify upload_file_to_azure uploads blob when connection string is present."""
    dummy_file = tmp_path / "dummy.parquet"
    dummy_file.write_text("dummy")

    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_blob = MagicMock()

    mock_client.get_container_client.return_value = mock_container
    mock_container.exists.return_value = True
    mock_container.get_blob_client.return_value = mock_blob

    with (
        patch("src.ingestion.storage.settings.azure_storage_connection_string", "mock_conn"),
        patch("azure.storage.blob.BlobServiceClient.from_connection_string", return_value=mock_client),
    ):
        result = upload_file_to_azure(dummy_file, "dummy.parquet", container_name="bronze")
        assert result is True
        mock_blob.upload_blob.assert_called_once()


def test_download_bronze_from_azure_unconfigured(tmp_path: Path) -> None:
    """Verify download_bronze_from_azure returns 0 when unconfigured."""
    with patch("src.ingestion.storage.settings.azure_storage_connection_string", ""):
        assert download_bronze_from_azure(target_dir=tmp_path) == 0


def test_download_bronze_from_azure_configured(tmp_path: Path) -> None:
    """Verify download_bronze_from_azure downloads blobs when configured."""
    mock_client = MagicMock()
    mock_container = MagicMock()
    mock_blob_client = MagicMock()

    mock_blob = MagicMock()
    mock_blob.name = "jobs/source=glints/dt=2026-10-21/data.parquet"
    mock_blob.size = 1234

    mock_client.get_container_client.return_value = mock_container
    mock_container.exists.return_value = True
    mock_container.list_blobs.return_value = [mock_blob]
    mock_container.get_blob_client.return_value = mock_blob_client
    mock_blob_client.download_blob.return_value.readall.return_value = b"parquet-bytes"

    with (
        patch("src.ingestion.storage.settings.azure_storage_connection_string", "mock_conn"),
        patch("azure.storage.blob.BlobServiceClient.from_connection_string", return_value=mock_client),
    ):
        count = download_bronze_from_azure(target_dir=tmp_path)
        assert count == 1
        downloaded_file = tmp_path / "bronze" / mock_blob.name
        assert downloaded_file.exists()
        assert downloaded_file.read_bytes() == b"parquet-bytes"


