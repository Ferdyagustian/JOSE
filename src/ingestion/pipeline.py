"""Main orchestration script for Bronze Layer Ingestion.

Executes Glints & JobStreet scrapers, runs YouTube metadata fetching with quota guards,
and saves partitioned Parquet files into the Bronze layer.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ingestion.glints_scraper import run_glints_scraper
from src.ingestion.jobstreet_scraper import run_jobstreet_scraper
from src.ingestion.storage import save_raw_jobs
from src.ingestion.youtube_fetcher import YouTubeFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_bronze_ingestion(
    glints_limit: int = 50,
    jobstreet_limit: int = 50,
    fetch_youtube: bool = True,
) -> dict[str, Any]:
    """Execute the full Bronze layer ingestion workflow."""
    logger.info("=== Starting Bronze Ingestion Pipeline ===")
    summary: dict[str, Any] = {
        "glints_count": 0,
        "jobstreet_count": 0,
        "youtube_count": 0,
        "job_parquet_files": [],
        "youtube_parquet_file": None,
    }

    # 1. Scrape Glints
    logger.info("Fetching Glints jobs (target limit: %d)...", glints_limit)
    glints_jobs = run_glints_scraper(limit=glints_limit)
    summary["glints_count"] = len(glints_jobs)

    # 2. Scrape JobStreet
    logger.info("Fetching JobStreet ICT jobs (target limit: %d)...", jobstreet_limit)
    jobstreet_jobs = run_jobstreet_scraper(limit=jobstreet_limit)
    summary["jobstreet_count"] = len(jobstreet_jobs)

    # 3. Save raw jobs into Bronze Parquet
    all_jobs = glints_jobs + jobstreet_jobs
    if all_jobs:
        saved_job_files = save_raw_jobs(all_jobs)
        summary["job_parquet_files"] = [str(p) for p in saved_job_files]

    # 4. Fetch YouTube Learning Videos
    if fetch_youtube:
        logger.info("Fetching YouTube tutorial metadata with cache guards...")
        fetcher = YouTubeFetcher()
        youtube_videos = fetcher.run_pipeline()
        summary["youtube_count"] = len(youtube_videos)

    logger.info(
        "=== Bronze Ingestion Completed: %d Glints, %d JobStreet, %d YouTube videos ===",
        summary["glints_count"],
        summary["jobstreet_count"],
        summary["youtube_count"],
    )
    return summary


if __name__ == "__main__":
    run_bronze_ingestion()
