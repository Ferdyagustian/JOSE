"""Pydantic data contracts for raw ingestion data (Bronze Layer).

Enforces schema validation and clean type conversions for job postings (Glints,
JobStreet, Kaggle) and YouTube learning videos.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobPostingRaw(BaseModel):
    """Raw job posting schema representing ingested data in Bronze Layer."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    job_id: str = Field(description="Unique identifier from the source portal")
    source: Literal["glints", "jobstreet", "kaggle", "mock"] = Field(
        description="Origin portal of the job posting"
    )
    job_title: str = Field(description="Title or role name of the job posting")
    company_name: str = Field(
        default="Confidential Company", description="Name of the hiring company"
    )
    company_industry: str | None = Field(default=None, description="Industry sector of the company")
    company_location: str | None = Field(
        default="Indonesia", description="Geographic location or city of the job"
    )
    employment_type: str | None = Field(
        default="Full-Time",
        description="Employment status (Full-Time, Contract, Internship, Part-Time)",
    )
    work_policy: str | None = Field(
        default="WFO",
        description="Work arrangement (Remote, Hybrid, WFO, On-site)",
    )
    experience_level: str | None = Field(
        default="Unspecified",
        description="Experience requirement (Fresh Graduate, Junior, Mid-Senior, Senior)",
    )
    salary_min: float | None = Field(default=None, description="Minimum salary range offered")
    salary_max: float | None = Field(default=None, description="Maximum salary range offered")
    currency: str | None = Field(default="IDR", description="Currency symbol/code (e.g. IDR, USD)")
    job_description: str = Field(
        default="", description="Full or snippet text of the job description"
    )
    job_url: str = Field(default="", description="Direct URL link to the original job posting")
    posted_at: str | None = Field(
        default=None, description="ISO timestamp or date string when job was posted"
    )
    scraped_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="UTC timestamp when the job was ingested",
    )

    @field_validator("company_name", mode="before")
    @classmethod
    def sanitize_company_name(cls, v: Any) -> str:
        if not v or str(v).strip().lower() in ("none", "null", ""):
            return "Confidential Company"
        return str(v).strip()

    @field_validator("company_industry", mode="before")
    @classmethod
    def sanitize_company_industry(cls, v: Any) -> str | None:
        if isinstance(v, dict):
            return str(v.get("name") or v.get("label") or "") or None
        if v:
            return str(v).strip()
        return None

    @field_validator("company_location", mode="before")
    @classmethod
    def sanitize_company_location(cls, v: Any) -> str | None:
        if isinstance(v, dict):
            return str(v.get("formattedName") or v.get("name") or v.get("city") or "Indonesia")
        if v:
            return str(v).strip()
        return "Indonesia"

    @field_validator("job_title", mode="before")
    @classmethod
    def sanitize_job_title(cls, v: Any) -> str:
        if not v:
            return "Software Engineer"
        return str(v).strip()


class YouTubeVideoRaw(BaseModel):
    """Raw metadata schema for a YouTube tutorial video associated with a tech skill."""

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    video_id: str = Field(description="YouTube unique video identifier")
    skill_name: str = Field(
        description="Technical skill name this video teaches (e.g. PySpark, dbt)"
    )
    video_title: str = Field(description="Title of the YouTube video")
    channel_name: str = Field(description="Name of the YouTube channel / creator")
    view_count: int = Field(default=0, description="Total view count of the video")
    like_count: int = Field(default=0, description="Total like count of the video")
    published_at: str | None = Field(
        default=None, description="ISO 8601 publication date timestamp"
    )
    video_url: str = Field(description="Direct URL to watch the video on YouTube")
    thumbnail_url: str = Field(default="", description="High resolution thumbnail image URL")
    fetched_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="UTC timestamp when metadata was retrieved",
    )
