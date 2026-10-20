"""Scraper for JobStreet Indonesia (SEEK Asia) ICT job postings.

Extracts structured job records from embedded window.SEEK_REDUX_DATA with
browser impersonation and robust circuit breakers.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any

from curl_cffi import requests

from src.ingestion.schemas import JobPostingRaw

logger = logging.getLogger(__name__)

JOBSTREET_BASE_URL = "https://www.jobstreet.co.id/id/jobs/in-Indonesia"
SEEK_DATA_MARKER = "SEEK_REDUX_DATA = "
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class JobStreetScraper:
    """Robust scraper for JobStreet Indonesia (SEEK)."""

    def __init__(self, timeout: int = 20) -> None:
        self.timeout = timeout
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update(
            {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://www.jobstreet.co.id/id",
            }
        )

    def _parse_job_item(self, item: dict[str, Any]) -> JobPostingRaw | None:
        """Map raw JobStreet/SEEK job record to normalized JobPostingRaw model."""
        job_id = item.get("id")
        title = item.get("title")
        if not job_id or not title:
            return None

        # Advertiser / Company
        advertiser = item.get("advertiser") or {}
        company_name = (
            advertiser.get("description") if isinstance(advertiser, dict) else str(advertiser)
        )

        # Location (prefer structured locations list with city/area)
        locations = item.get("locations") or []
        location_label = None
        if isinstance(locations, list) and len(locations) > 0 and isinstance(locations[0], dict):
            location_label = locations[0].get("label")
        location = item.get("location")
        area = item.get("area")
        company_location = location_label or area or location or "Indonesia"

        # Employment type & work policy
        work_type = item.get("workType") or "Full-Time"

        # Detect work policy from teaser / bullet points
        teaser = item.get("teaser") or ""
        bullets = item.get("bulletPoints") or []
        combined_text = f"{title} {teaser} {' '.join(bullets)}".lower()

        if "remote" in combined_text or "work from home" in combined_text or "wfh" in combined_text:
            work_policy = "Remote"
        elif "hybrid" in combined_text:
            work_policy = "Hybrid"
        else:
            work_policy = "WFO"

        # Salary parsing (e.g. 'Rp 8.000.000 - Rp 12.000.000 per bulan' or 'Rp 8.000.000 per month')
        salary_str = str(item.get("salaryLabel") or item.get("salary") or "").strip()
        salary_min = None
        salary_max = None
        currency = "IDR"

        if salary_str and salary_str.lower() not in ("none", "null", ""):
            is_yearly = any(y in salary_str.lower() for y in ("year", "tahun", "annually"))
            nums = re.findall(r"\d[\d.,]*\d|\d+", salary_str)
            clean_nums = []
            for n in nums:
                clean = re.sub(r"[^\d]", "", n)
                if clean.isdigit() and len(clean) >= 4:
                    val = float(clean)
                    if is_yearly:
                        val = round(val / 12.0)
                    clean_nums.append(val)
            if len(clean_nums) == 1:
                salary_min = clean_nums[0]
            elif len(clean_nums) >= 2:
                salary_min = min(clean_nums[0], clean_nums[1])
                salary_max = max(clean_nums[0], clean_nums[1])

        # Description
        description = f"{teaser}. {' '.join(bullets)}" if bullets else teaser

        return JobPostingRaw(
            job_id=str(job_id),
            source="jobstreet",
            job_title=title,
            company_name=company_name or "Confidential Company",
            company_industry="Information & Communication Technology",
            company_location=str(company_location),
            employment_type=str(work_type),
            work_policy=work_policy,
            experience_level="Unspecified",
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            job_description=description or title,
            job_url=f"https://www.jobstreet.co.id/id/job/{job_id}",
            posted_at=item.get("listingDate"),
        )

    def fetch_jobs(
        self,
        keyword: str | None = "software-engineer",
        classification: str = "6281",  # ICT category
        limit: int = 50,
        max_retries: int = 3,
    ) -> list[JobPostingRaw]:
        """Fetch latest ICT jobs in Indonesia from JobStreet."""
        url = f"https://www.jobstreet.co.id/id/{keyword}-jobs" if keyword else JOBSTREET_BASE_URL
        params: dict[str, str] = {
            "sortmode": "ListedDate",
        }
        if not keyword:
            params["classification"] = classification

        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    sleep_time = random.uniform(2.0, 4.0) * attempt
                    logger.info("Retrying JobStreet in %.1f seconds...", sleep_time)
                    time.sleep(sleep_time)

                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    text = response.text
                    idx = text.find(SEEK_DATA_MARKER)
                    if idx == -1:
                        logger.warning("JobStreet SEEK_REDUX_DATA marker not found.")
                        return []

                    json_start = idx + len(SEEK_DATA_MARKER)
                    decoder = json.JSONDecoder()
                    data, _ = decoder.raw_decode(text[json_start:])

                    results_node = data.get("results", {})
                    raw_jobs = results_node.get("results", {}).get("jobs", []) or results_node.get(
                        "jobs", []
                    )

                    results: list[JobPostingRaw] = []
                    for item in raw_jobs:
                        parsed = self._parse_job_item(item)
                        if parsed:
                            results.append(parsed)
                        if len(results) >= limit:
                            break

                    logger.info(
                        "Successfully fetched %d JobStreet jobs (keyword: %s).",
                        len(results),
                        keyword or classification,
                    )
                    return results

                if response.status_code in (403, 429):
                    logger.warning(
                        "JobStreet rate limited / blocked (HTTP %d). Circuit breaker triggered.",
                        response.status_code,
                    )
                    break

                logger.warning("JobStreet returned unexpected status %d", response.status_code)

            except Exception as exc:
                logger.warning("JobStreet scraper error on attempt %d: %s", attempt, exc)

        logger.info("JobStreet scraper completed with 0 results (circuit breaker active).")
        return []


def run_jobstreet_scraper(limit: int = 50) -> list[JobPostingRaw]:
    """Helper entry point for pipeline execution."""
    scraper = JobStreetScraper()
    keywords = ["software-engineer", "data-engineer"]
    all_jobs: list[JobPostingRaw] = []
    seen_ids: set[str] = set()

    for kw in keywords:
        jobs = scraper.fetch_jobs(keyword=kw, limit=limit // len(keywords))
        for j in jobs:
            if j.job_id not in seen_ids:
                seen_ids.add(j.job_id)
                all_jobs.append(j)
        time.sleep(random.uniform(1.0, 2.0))

    return all_jobs
