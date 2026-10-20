"""Bronze storage helper for partitioned Parquet persistence.

Saves raw ingested data locally or to Azure Blob Storage following Medallion
Bronze partition conventions:
  bronze/jobs/source={source}/dt={YYYY-MM-DD}/data.parquet
  bronze/youtube/dt={YYYY-MM-DD}/videos.parquet
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import settings
from src.ingestion.schemas import JobPostingRaw, YouTubeVideoRaw

logger = logging.getLogger(__name__)


def get_base_data_dir() -> Path:
    """Return the local base data directory, ensuring it exists."""
    data_dir = settings.local_data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def save_raw_jobs(
    jobs: Sequence[JobPostingRaw],
    base_dir: Path | str | None = None,
) -> list[Path]:
    """Save raw job postings partitioned by source and date into Parquet."""
    if not jobs:
        logger.info("No jobs to save.")
        return []

    target_dir = Path(base_dir) if base_dir else get_base_data_dir()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    # Group jobs by source
    grouped: dict[str, list[dict]] = {}
    for job in jobs:
        grouped.setdefault(job.source, []).append(job.model_dump())

    saved_paths: list[Path] = []
    for source, records in grouped.items():
        partition_dir = target_dir / "bronze" / "jobs" / f"source={source}" / f"dt={today_str}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        parquet_file = partition_dir / "data.parquet"

        table = pa.Table.from_pylist(records)
        pq.write_table(table, parquet_file, compression="SNAPPY")
        logger.info("Saved %d %s jobs to %s", len(records), source, parquet_file)
        saved_paths.append(parquet_file)

        # Sync to Azure Blob Storage if configured
        if settings.is_azure_configured:
            blob_path = f"jobs/source={source}/dt={today_str}/data.parquet"
            upload_file_to_azure(parquet_file, blob_path, container_name=settings.bronze_container)

    return saved_paths


def upload_file_to_azure(
    local_file: Path,
    blob_name: str,
    container_name: str | None = None,
) -> bool:
    """Upload a local file to Azure Blob Storage container if configured."""
    if not settings.is_azure_configured:
        return False
    try:
        from azure.storage.blob import BlobServiceClient

        container = container_name or settings.bronze_container
        service_client = BlobServiceClient.from_connection_string(
            settings.azure_storage_connection_string
        )
        container_client = service_client.get_container_client(container)
        if not container_client.exists():
            container_client.create_container()

        blob_client = container_client.get_blob_client(blob_name)
        with open(local_file, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
        logger.info("Uploaded %s to Azure container '%s' as %s", local_file.name, container, blob_name)
        return True
    except Exception as exc:
        logger.warning("Failed to upload %s to Azure Blob: %s", local_file, exc)
        return False


def save_raw_youtube_videos(
    videos: Sequence[YouTubeVideoRaw],
    base_dir: Path | str | None = None,
) -> Path | None:
    """Save raw YouTube video metadata into the Bronze partition."""
    if not videos:
        logger.info("No YouTube videos to save.")
        return None

    target_dir = Path(base_dir) if base_dir else get_base_data_dir()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    partition_dir = target_dir / "bronze" / "youtube" / f"dt={today_str}"
    partition_dir.mkdir(parents=True, exist_ok=True)
    parquet_file = partition_dir / "videos.parquet"

    records = [v.model_dump() for v in videos]
    table = pa.Table.from_pylist(records)
    pq.write_table(table, parquet_file, compression="SNAPPY")
    logger.info("Saved %d YouTube videos to %s", len(records), parquet_file)

    # Sync to Azure Blob Storage if configured
    if settings.is_azure_configured:
        blob_path = f"youtube/dt={today_str}/videos.parquet"
        upload_file_to_azure(parquet_file, blob_path, container_name=settings.bronze_container)

    return parquet_file


def load_all_cached_youtube_skills(base_dir: Path | str | None = None) -> set[str]:
    """Scan existing Bronze YouTube parquet files to identify cached skills."""
    target_dir = Path(base_dir) if base_dir else get_base_data_dir()
    youtube_bronze = target_dir / "bronze" / "youtube"
    if not youtube_bronze.exists():
        return set()

    parquet_files = list(youtube_bronze.glob("**/videos.parquet"))
    if not parquet_files:
        return set()

    try:
        # Use DuckDB to query all parquet files in one shot
        query = f"SELECT DISTINCT skill_name FROM read_parquet('{youtube_bronze}/**/*.parquet')"
        con = duckdb.connect(":memory:")
        df = con.execute(query).df()
        con.close()
        return set(df["skill_name"].dropna().unique())
    except Exception as e:
        logger.warning("Could not scan cached YouTube skills: %s", e)
        return set()
