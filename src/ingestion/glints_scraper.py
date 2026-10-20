"""Scraper for Glints Indonesia IT job postings.

Utilizes curl_cffi with Chrome 120 browser impersonation to bypass basic WAFs
and extract structured job records embedded in Next.js __NEXT_DATA__.
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

GLINTS_EXPLORE_URL = "https://glints.com/id/opportunities/jobs/explore"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class GlintsScraper:
    """Robust scraper for Glints Indonesia jobs."""

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
                "Referer": "https://glints.com/id",
            }
        )

    def _parse_job_item(self, item: dict[str, Any]) -> JobPostingRaw | None:
        """Map raw Glints JSON object to normalized JobPostingRaw model."""
        job_id = item.get("id")
        title = item.get("title")
        if not job_id or not title:
            return None

        # Company details
        company = item.get("company") or {}
        company_name = company.get("name") if isinstance(company, dict) else str(company)
        raw_industry = company.get("industry") if isinstance(company, dict) else None
        if isinstance(raw_industry, dict):
            company_industry = raw_industry.get("name")
        else:
            company_industry = str(raw_industry) if raw_industry else None

        # Location details (extract human city instead of raw HierarchicalLocation dict)
        raw_city = item.get("city")
        city_name = raw_city.get("name") if isinstance(raw_city, dict) else raw_city
        raw_location = item.get("location")
        loc_name = None
        if isinstance(raw_location, dict):
            parents = raw_location.get("parents") or []
            for p in parents:
                if isinstance(p, dict) and p.get("administrativeLevelName") in ("City", "Kabupaten"):
                    loc_name = p.get("name") or p.get("formattedName")
                    break
            if not loc_name:
                loc_name = raw_location.get("name") or raw_location.get("formattedName")
        elif isinstance(raw_location, str):
            loc_name = raw_location

        company_location = city_name or loc_name or "Indonesia"

        # Salary details
        salaries = item.get("salaries") or []
        salary_min = None
        salary_max = None
        currency = "IDR"

        if salaries and isinstance(salaries, list) and len(salaries) > 0:
            first_salary = salaries[0]
            salary_min = first_salary.get("minAmount") or first_salary.get("MinAmount")
            salary_max = first_salary.get("maxAmount") or first_salary.get("MaxAmount")
            currency = first_salary.get("currencyCode") or first_salary.get("CurrencyCode") or "IDR"
        else:
            salary_min = item.get("minSalary")
            salary_max = item.get("maxSalary")
            currency = item.get("salaryCurrency") or item.get("currency") or "IDR"

        # Work policy & employment type
        work_policy = item.get("workArrangementOption") or item.get("workplaceType") or "WFO"
        employment_type = item.get("type") or "Full-Time"

        # Experience level
        min_exp = item.get("minYearsOfExperience")
        max_exp = item.get("maxYearsOfExperience")
        if min_exp is not None and max_exp is not None:
            experience_level = f"{min_exp}-{max_exp} yrs"
        elif min_exp is not None:
            experience_level = f"{min_exp}+ yrs"
        else:
            experience_level = "Unspecified"

        # Skills & description snippet
        skills_raw = item.get("skills") or []
        skill_names = [s.get("name") for s in skills_raw if isinstance(s, dict) and s.get("name")]
        skills_text = f"Required Skills: {', '.join(skill_names)}. " if skill_names else ""
        description = skills_text + (item.get("description") or title)

        return JobPostingRaw(
            job_id=str(job_id),
            source="glints",
            job_title=title,
            company_name=company_name or "Confidential Company",
            company_industry=company_industry,
            company_location=str(company_location),
            employment_type=str(employment_type),
            work_policy=str(work_policy),
            experience_level=experience_level,
            salary_min=float(salary_min) if salary_min is not None else None,
            salary_max=float(salary_max) if salary_max is not None else None,
            currency=str(currency),
            job_description=description,
            job_url=f"https://glints.com/id/opportunities/jobs/{job_id}",
            posted_at=item.get("createdAt"),
        )

    def fetch_jobs(
        self,
        keyword: str = "software engineer",
        limit: int = 50,
        last_updated: str | None = None,
        max_retries: int = 3,
    ) -> list[JobPostingRaw]:
        """Fetch latest IT jobs in Indonesia from Glints.

        Includes circuit breaker to handle transient 403s or network errors gracefully.
        """
        params: dict[str, Any] = {
            "country": "ID",
            "keyword": keyword,
        }
        if last_updated:
            params["lastUpdated"] = last_updated

        for attempt in range(1, max_retries + 1):
            try:
                # Add jitter delay between attempts
                if attempt > 1:
                    sleep_time = random.uniform(2.0, 4.0) * attempt
                    logger.info("Retrying Glints in %.1f seconds...", sleep_time)
                    time.sleep(sleep_time)

                response = self.session.get(
                    GLINTS_EXPLORE_URL,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    match = re.search(
                        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                        response.text,
                    )
                    if not match:
                        logger.warning("Glints __NEXT_DATA__ tag not found.")
                        return []

                    payload = json.loads(match.group(1))
                    page_props = payload.get("props", {}).get("pageProps", {})
                    initial_jobs = page_props.get("initialJobs", {})
                    raw_items = initial_jobs.get("jobsInPage", [])

                    results: list[JobPostingRaw] = []
                    for item in raw_items:
                        parsed = self._parse_job_item(item)
                        if parsed:
                            results.append(parsed)
                        if len(results) >= limit:
                            break

                    logger.info(
                        "Successfully fetched %d Glints jobs for '%s'.",
                        len(results),
                        keyword,
                    )
                    return results

                if response.status_code in (403, 429):
                    logger.warning(
                        "Glints rate limited / blocked (HTTP %d). Circuit breaker triggered.",
                        response.status_code,
                    )
                    break

                logger.warning("Glints returned unexpected status %d", response.status_code)

            except Exception as exc:
                logger.warning("Glints scraper error on attempt %d: %s", attempt, exc)

        logger.info("Glints scraper completed with 0 results (circuit breaker active).")
        return []


def run_glints_scraper(limit: int = 50) -> list[JobPostingRaw]:
    """Helper entry point for pipeline execution."""
    scraper = GlintsScraper()
    keywords = ["software engineer", "data engineer"]
    all_jobs: list[JobPostingRaw] = []
    seen_ids: set[str] = set()

    for kw in keywords:
        jobs = scraper.fetch_jobs(keyword=kw, limit=limit // len(keywords))
        for j in jobs:
            if j.job_id not in seen_ids:
                seen_ids.add(j.job_id)
                all_jobs.append(j)

        # Politeness delay
        time.sleep(random.uniform(1.0, 2.0))

    return all_jobs
